
        // As variáveis SUPABASE_URL e SUPABASE_ANON_KEY são injetadas pelo server.py
        // via window.__SUPABASE_URL e window.__SUPABASE_KEY no bloco <script> inline do HTML.
        const SUPABASE_URL      = window.__SUPABASE_URL;
        const SUPABASE_ANON_KEY = window.__SUPABASE_KEY;
        const API_BASE = '';  // Relativo ao servidor atual — funciona local e em produção


        // Estado global
        let _db = null;
        let _session = null;
        let _jobsPollingTimer = null;

        function escapeHtml(str) {
            if (!str) return '-';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        // ── Inicialização ──────────────────────────────────────────────

        async function init() {
            const { createClient } = supabase;
            _db = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

            showLoading();

            // Detecta token de recovery no hash da URL (vindo do email de redefinição)
            const hashParams = new URLSearchParams(window.location.hash.substring(1));
            if (hashParams.get('type') === 'recovery' && hashParams.get('access_token')) {
                const { error } = await _db.auth.setSession({
                    access_token:  hashParams.get('access_token'),
                    refresh_token: hashParams.get('refresh_token') || ''
                });
                document.getElementById('loading').style.display = 'none';
                if (!error) {
                    showResetPassword();
                } else {
                    showLogin();
                }
                return;
            }

            const { data: { session } } = await _db.auth.getSession();

            if (session) {
                _session = session;
                await loadDashboard();
            } else {
                hideLoading();
                showLogin();
            }
        }

        // ── Autenticação ───────────────────────────────────────────────

        function showLogin() {
            document.getElementById('loading').style.display        = 'none';
            document.getElementById('login').style.display          = 'flex';
            document.getElementById('dashboard').style.display      = 'none';
            document.getElementById('reset-password').style.display = 'none';
        }

        function showResetPassword() {
            document.getElementById('loading').style.display        = 'none';
            document.getElementById('login').style.display          = 'none';
            document.getElementById('dashboard').style.display      = 'none';
            document.getElementById('reset-password').style.display = 'flex';
        }

        async function handleLogin(e) {
            e.preventDefault();
            const email    = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            const btn      = document.getElementById('login-btn');
            const errEl    = document.getElementById('login-error');

            btn.textContent = 'Entrando...';
            btn.disabled = true;
            errEl.style.display = 'none';

            const { data, error } = await _db.auth.signInWithPassword({ email, password });

            if (error) {
                errEl.textContent = 'Email ou senha incorretos';
                errEl.style.display = 'block';
                btn.textContent = 'Entrar';
                btn.disabled = false;
                return;
            }

            _session = data.session;
            document.getElementById('login').style.display = 'none';
            showLoading();
            await loadDashboard();
        }

        function togglePwField(fieldId, btn) {
            const input = document.getElementById(fieldId);
            if (input.type === 'password') {
                input.type = 'text';
                btn.innerHTML = '&#128065;&#65039;';
            } else {
                input.type = 'password';
                btn.innerHTML = '&#128065;';
            }
        }

        function togglePw() {
            togglePwField('login-password', document.getElementById('pw-toggle-btn'));
        }

        async function handleSetNewPassword(e) {
            e.preventDefault();
            const newPw     = document.getElementById('new-password').value;
            const confirmPw = document.getElementById('confirm-password').value;
            const errEl     = document.getElementById('reset-error');
            const infoEl    = document.getElementById('reset-info');
            const btn       = document.getElementById('reset-btn');

            errEl.style.display  = 'none';
            infoEl.style.display = 'none';

            if (newPw !== confirmPw) {
                errEl.textContent   = 'As senhas não coincidem.';
                errEl.style.display = 'block';
                return;
            }

            btn.textContent = 'Salvando...';
            btn.disabled = true;

            const { error } = await _db.auth.updateUser({ password: newPw });

            if (error) {
                errEl.textContent   = 'Erro: ' + error.message;
                errEl.style.display = 'block';
                btn.textContent     = 'Salvar nova senha';
                btn.disabled        = false;
            } else {
                infoEl.textContent   = '✅ Senha atualizada! Redirecionando para o login...';
                infoEl.style.display = 'block';
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            }
        }

        async function handleForgotPassword() {
            const email  = document.getElementById('login-email').value.trim();
            const errEl  = document.getElementById('login-error');
            const infoEl = document.getElementById('login-info');
            errEl.style.display  = 'none';
            infoEl.style.display = 'none';

            if (!email) {
                errEl.textContent    = 'Digite seu email acima antes de redefinir a senha.';
                errEl.style.display  = 'block';
                return;
            }

            try {
                const resp = await fetch('/api/auth/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                const result = await resp.json();
                if (result.ok) {
                    infoEl.textContent   = 'Email enviado! Verifique sua caixa de entrada.';
                    infoEl.style.display = 'block';
                } else {
                    errEl.textContent   = 'Erro: ' + result.error;
                    errEl.style.display = 'block';
                }
            } catch (e) {
                errEl.textContent   = 'Erro de rede. Tente novamente.';
                errEl.style.display = 'block';
            }
        }

        async function handleLogout() {
            await _db.auth.signOut();
            _session = null;
            stopJobsPolling();
            window.location.reload();
        }

        // ── Dashboard ──────────────────────────────────────────────────

        async function loadDashboard() {
            hideLoading();
            showDashboard();
            switchTab('leads');
        }

        // ── Abas ───────────────────────────────────────────────────────

        function switchTab(tabName) {
            // Atualizar botões
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === tabName);
            });

            // Mostrar conteúdo correto
            document.querySelectorAll('.tab-content').forEach(el => {
                el.style.display = 'none';
                el.classList.remove('active');
            });
            const active = document.getElementById(`tab-${tabName}`);
            if (active) {
                active.style.display = 'block';
                active.classList.add('active');
            }

            // Parar polling de jobs se sair da aba
            if (tabName !== 'jobs') stopJobsPolling();

            // Carregar dados da aba selecionada
            if (tabName === 'leads')     loadLeadsTab();
            if (tabName === 'clientes')  loadClientesTab();
            if (tabName === 'auditoria') loadAuditoriaTab();
            if (tabName === 'jobs')      loadJobsTab();
            if (tabName === 'sites')     loadSitesTab();
        }

        // ── Aba Leads ──────────────────────────────────────────────────

        async function loadLeadsTab() {
            showLoading();

            // Usar backend autenticado em vez de Supabase direto
            const token = _session?.access_token;
            try {
                const resp = await fetch(`${API_BASE}/api/leads?limit=200`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                hideLoading();
                showDashboard();

                if (!resp.ok) { renderLeadsError(); return; }

                const data = await resp.json();
                const leads = data.leads || [];
                renderCards(leads);
                renderRanking(leads);
                renderTable(leads);
            } catch (err) {
                hideLoading();
                showDashboard();
                renderLeadsError();
            }
        }

        function renderLeadsError() {
            document.getElementById('leads-table').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <h3>Erro ao carregar leads</h3>
                    <p>Verifique se o backend está rodando.</p>
                </div>
            `;
        }

        // ── Aba Clientes ───────────────────────────────────────────────

        async function loadClientesTab() {
            const el = document.getElementById('clientes-list');
            el.innerHTML = '<div class="empty-state"><div class="spinner"></div></div>';

            const token = _session?.access_token;
            try {
                const resp = await fetch(`${API_BASE}/api/clientes`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (!resp.ok) {
                    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Erro ao carregar clientes</h3></div>`;
                    return;
                }

                const { clientes } = await resp.json();

                if (!clientes || clientes.length === 0) {
                    el.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">🏢</div>
                            <h3>Nenhum cliente cadastrado</h3>
                            <p>Gere o primeiro site pelo wizard para criar um cliente.</p>
                        </div>
                    `;
                    return;
                }

                el.innerHTML = `<div class="clientes-grid">${clientes.map(renderClienteCard).join('')}</div>`;
            } catch (err) {
                el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Erro ao carregar clientes</h3></div>`;
            }
        }

        function renderClienteCard(c) {
            const siteUrl = c.site_url || `https://${c.subdomain}.autoridade.digital`;
            const lastGen = c.last_generated
                ? new Date(c.last_generated).toLocaleDateString('pt-BR')
                : 'Nunca';

            const badgeClass = { live: 'badge-live', pending: 'badge-pending',
                                 generating: 'badge-generating', error: 'badge-error' }[c.status] || 'badge-pending';

            return `
                <div class="cliente-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">
                        <div class="cliente-card-name">${escapeHtml(c.empresa_nome)}</div>
                        <span class="badge ${badgeClass}">${c.status}</span>
                    </div>
                    <div class="cliente-card-domain">
                        <a href="${escapeHtml(siteUrl)}" target="_blank">${escapeHtml(siteUrl)}</a>
                    </div>
                    <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:12px">
                        ${escapeHtml(c.categoria || '')}
                    </div>
                    <div class="cliente-card-footer">
                        <span style="font-size:0.78rem;color:var(--text-muted)">
                            Gerado: ${lastGen}
                        </span>
                        <div style="display:flex;gap:6px;flex-wrap:wrap">
                            <a href="${escapeHtml(siteUrl)}" target="_blank" rel="noopener"
                               style="padding:4px 10px;font-size:0.78rem;background:#7c3aed;
                                      border-radius:6px;text-decoration:none;color:#fff;">
                               🌐 Ver Site
                            </a>
                            <button onclick="openMagicEdit('${escapeHtml(c.id)}', '${escapeHtml(c.empresa_nome)}', 'cliente')"
                               style="padding:4px 10px;font-size:0.78rem;background:#0f766e;
                                      border:none;border-radius:6px;color:#fff;cursor:pointer;
                                      font-family:inherit;">
                               ✨ Magic Edit
                            </button>
                            <button onclick="redeployCliente('${escapeHtml(c.id)}', '${escapeHtml(c.empresa_nome)}')"
                               style="padding:4px 10px;font-size:0.78rem;background:#0369a1;
                                      border:none;border-radius:6px;color:#fff;cursor:pointer;
                                      font-family:inherit;" title="Republica usando o cache existente (rápido, sem IA)">
                               ⚡ Redeploy
                            </button>
                            <button onclick="regenerarCliente('${escapeHtml(c.id)}', '${escapeHtml(c.empresa_nome)}')"
                               style="padding:4px 10px;font-size:0.78rem;background:#b45309;
                                      border:none;border-radius:6px;color:#fff;cursor:pointer;
                                      font-family:inherit;">
                               🔄 Regenerar
                            </button>
                            <button onclick="abrirRelatorio('${escapeHtml(c.id)}', '${escapeHtml(c.empresa_nome)}')" style="padding:4px 10px;font-size:0.78rem;background:#1e3a5f;border:none;border-radius:6px;color:#7dd3fc;cursor:pointer;font-family:inherit;" title="Ver relatorio da ultima geracao">
                               📊 Relatório
                            </button>
                            <button onclick="deletarCliente('${escapeHtml(c.id)}', '${escapeHtml(c.empresa_nome)}', '${escapeHtml(c.subdomain)}')"
                               style="padding:4px 10px;font-size:0.78rem;background:#7f1d1d;
                                      border:none;border-radius:6px;color:#fca5a5;cursor:pointer;
                                      font-family:inherit;" title="Remove cliente, site, DNS e projeto Pages">
                               🗑️ Deletar
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }

        function filterLeadsByClient(subdomain) {
            switchTab('leads');
        }

        async function redeployCliente(clienteId, empresaNome) {
            if (!confirm(`Republicar "${empresaNome}" usando o cache existente? (rápido, sem IA)`)) return;
            const token = _session?.access_token;
            try {
                const resp = await fetch(`${API_BASE}/api/clientes/${clienteId}/redeploy`, {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${token}` }
                });
                const data = await resp.json();
                if (resp.ok) {
                    alert(`⚡ Fast Redeploy iniciado! Job ID: ${data.job_id}\nAcompanhe na aba Jobs.`);
                    switchTab('jobs');
                } else {
                    alert('❌ ' + (data.detail || JSON.stringify(data)));
                }
            } catch(e) {
                alert('❌ Erro de rede: ' + e.message);
            }
        }

        async function regenerarCliente(clienteId, empresaNome) {
            if (!confirm(`Regenerar o site de "${empresaNome}" completamente? Isso vai criar um novo job e pode levar ~10-15 min.`)) return;

            const token = _session?.access_token;
            try {
                const resp = await fetch(`${API_BASE}/api/clientes/${clienteId}/regenerar`, {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
                });
                const data = await resp.json();
                if (resp.ok) {
                    openProgressModal(data.job_id, clienteId, empresaNome);
                } else {
                    alert('❌ Erro: ' + (data.detail || JSON.stringify(data)));
                }
            } catch(e) {
                alert('❌ Erro de rede: ' + e.message);
            }
        }


        // ── Progress Modal ────────────────────────────────────────────────────
        const STEP_LABELS = {
            queue:              'Na fila...',
            validating:         'Verificando dados...',
            mixing:             'Configurando conteúdo...',
            hero:               'Criando imagem hero...',
            home_data:          'Gerando dados da homepage...',
            topics:             'Pesquisando tópicos de SEO...',
            home_page:          'Construindo homepage...',
            subpages:           'Gerando subpáginas...',
            validating_quality: 'Verificando qualidade...',
            packaging:          'Empacotando arquivos...',
            sitemap:            'Gerando sitemap...',
            deploying:          'Publicando o site...',
            done:               '✅ Site publicado!',
        };

        let _pgInterval  = null;
        let _pgTimer     = null;
        let _pgClientId  = null;
        let _pgJobId     = null;

        function openProgressModal(jobId, clienteId, empresaNome) {
            _pgJobId    = jobId;
            _pgClientId = clienteId;
            const start = Date.now();

            document.getElementById('pg-empresa').textContent  = empresaNome || '';
            document.getElementById('pg-title').textContent    = 'Gerando site...';
            document.getElementById('pg-icon').textContent     = '⚙️';
            document.getElementById('pg-bar').style.width      = '0%';
            document.getElementById('pg-pct').textContent      = '0%';
            document.getElementById('pg-step').textContent     = 'Na fila...';
            document.getElementById('pg-status').textContent   = 'Aguardando';
            document.getElementById('pg-log').textContent      = '...';
            document.getElementById('pg-jobid').textContent    = jobId || '';
            document.getElementById('pg-time').textContent     = '0s';
            document.getElementById('pg-close-btn').style.display = 'none';
            document.getElementById('progress-modal').style.display = 'flex';

            // Timer ao-vivo
            _pgTimer = setInterval(() => {
                const elapsed = Math.floor((Date.now() - start) / 1000);
                const m = Math.floor(elapsed / 60), s = elapsed % 60;
                document.getElementById('pg-time').textContent = m > 0 ? `${m}m ${s}s` : `${s}s`;
            }, 1000);

            // Polling a cada 2.5s
            _pgInterval = setInterval(async () => {
                try {
                    const token = _session?.access_token;
                    const r = await fetch(`${API_BASE}/api/jobs/${jobId}/status`, {
                        headers: { Authorization: `Bearer ${token}` }
                    });
                    if (!r.ok) return;
                    const job = await r.json();

                    const pct = job.progress_pct || 0;
                    document.getElementById('pg-bar').style.width  = pct + '%';
                    document.getElementById('pg-pct').textContent  = pct + '%';
                    document.getElementById('pg-step').textContent = STEP_LABELS[job.step] || job.step || '...';
                    document.getElementById('pg-status').textContent = job.status || '';

                    const logs = job.logs || [];
                    if (logs.length) {
                        const last = logs[logs.length - 1];
                        document.getElementById('pg-log').textContent = last.message || '...';
                    }

                    if (job.status === 'complete') {
                        clearInterval(_pgInterval);
                        clearInterval(_pgTimer);
                        document.getElementById('pg-bar').style.width   = '100%';
                        document.getElementById('pg-pct').textContent   = '100%';
                        document.getElementById('pg-icon').textContent  = '✅';
                        document.getElementById('pg-title').textContent = 'Site publicado com sucesso!';
                        setTimeout(() => {
                            document.getElementById('progress-modal').style.display = 'none';
                            if (_pgClientId) showRelatorio(_pgClientId, empresaNome);
                            loadClientesTab();
                        }, 1500);
                    } else if (job.status === 'failed') {
                        clearInterval(_pgInterval);
                        clearInterval(_pgTimer);
                        document.getElementById('pg-icon').textContent  = '❌';
                        document.getElementById('pg-title').textContent = 'Falha na geração';
                        document.getElementById('pg-status').textContent = 'failed';
                        document.getElementById('pg-log').textContent   = job.error_message || 'Erro desconhecido';
                        document.getElementById('pg-close-btn').style.display = 'block';
                    }
                } catch(e) { /* ignora erros de rede transitórios */ }
            }, 2500);
        }

        function closeProgressModal() {
            if (_pgInterval) clearInterval(_pgInterval);
            if (_pgTimer)    clearInterval(_pgTimer);
            document.getElementById('progress-modal').style.display = 'none';
        }

        // ── Relatório Modal ────────────────────────────────────────────────────
        async function showRelatorio(clienteId, empresaNome, subdomain) {
            const token = _session?.access_token;
            try {
                const r = await fetch(`${API_BASE}/api/clientes/${clienteId}/ultimo-relatorio`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                const rel = r.ok ? await r.json() : {};
                // _no_history = sem geracao completa ainda (so Redeploy/Fast Sync)
                if (!r.ok || rel._no_history) {
                    _renderRelatorioSimples(clienteId, empresaNome, rel.subdomain || subdomain);
                    return;
                }
                _renderRelatorio(rel, clienteId, empresaNome);
            } catch(e) {
                console.warn('Relatorio:', e);
                _renderRelatorioSimples(clienteId, empresaNome, subdomain);
            }
        }

        function _renderRelatorioSimples(clienteId, empresaNome, subdomain) {
            const slug = subdomain || clienteId;
            document.getElementById('rel-header').innerHTML = `
                <div style="background:linear-gradient(135deg,#7c3aed22,#0f766e22);border-radius:10px;padding:14px 18px;">
                    <div style="font-weight:700;font-size:1rem;">${escapeHtml(empresaNome || '')}</div>
                    <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">✅ Geração concluída com sucesso!</div>
                </div>`;
            ['rel-pages','rel-tempo','rel-custo','rel-qualidade'].forEach(id => {
                document.getElementById(id).textContent = '—';
            });
            document.getElementById('rel-detalhes').innerHTML = `
                <div style="color:var(--text-muted);padding:8px 0;">O relatório detalhado estará disponível após a próxima geração completa.</div>`;
            document.getElementById('rel-acoes').innerHTML = `
                <a href="https://${escapeHtml(slug)}.autoridade.digital" target="_blank" style="
                    flex:1;padding:12px;background:#7c3aed;color:#fff;border-radius:10px;
                    text-decoration:none;text-align:center;font-weight:600;font-size:0.9rem;">
                    🌐 Ver Site
                </a>
                <a href="/api/download/${escapeHtml(slug)}" download style="
                    flex:1;padding:12px;background:#0f766e;color:#fff;border-radius:10px;
                    text-decoration:none;text-align:center;font-weight:600;font-size:0.9rem;">
                    📥 Baixar ZIP
                </a>
                <button onclick="closeRelatorio()" style="
                    padding:12px 20px;background:var(--bg);border:1px solid var(--border);
                    border-radius:10px;cursor:pointer;font-family:inherit;color:var(--text);">
                    Fechar
                </button>`;
            document.getElementById('relatorio-modal').style.display = 'flex';
        }

        function _renderRelatorio(rel, clienteId, empresaNome) {
            const totalPages = rel.total_pages_generated || 0;
            const validPages = rel.valid_pages || 0;
            const duration   = rel.duration_seconds || 0;
            const costBrl    = (rel.cost_brl || 0).toFixed(4);
            const qualidade  = totalPages > 0 ? Math.round(validPages / totalPages * 100) + '%' : '—';
            const mins = Math.floor(duration / 60), secs = duration % 60;
            const tempoStr  = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
            const geradoEm  = rel.created_at ? new Date(rel.created_at).toLocaleString('pt-BR') : '—';
            const tokens    = (rel.tokens_used || 0).toLocaleString('pt-BR');
            const provedor  = rel.gemini_tokens > 0 ? 'Gemini' : rel.openai_tokens > 0 ? 'OpenAI' : '—';
            const subdomain = rel.subdomain || clienteId;

            document.getElementById('rel-header').innerHTML = `
                <div style="background:linear-gradient(135deg,#7c3aed22,#0f766e22);border-radius:10px;padding:14px 18px;">
                    <div style="font-weight:700;font-size:1rem;">${escapeHtml(empresaNome || '')}</div>
                    <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">Gerado em ${geradoEm}</div>
                </div>`;

            document.getElementById('rel-pages').textContent     = totalPages;
            document.getElementById('rel-tempo').textContent     = tempoStr;
            document.getElementById('rel-custo').textContent     = 'R$ ' + costBrl;
            document.getElementById('rel-qualidade').textContent = qualidade;

            document.getElementById('rel-detalhes').innerHTML = `
                <div>🧠 <b>IA usada:</b> ${provedor}</div>
                <div>📝 <b>Tokens consumidos:</b> ${tokens}</div>
                <div>✅ <b>Páginas válidas:</b> ${validPages} de ${totalPages}</div>
                ${rel.error_pages > 0 ? `<div>⚠️ <b>Páginas com erro:</b> ${rel.error_pages}</div>` : ''}
            `;

            document.getElementById('rel-acoes').innerHTML = `
                <a href="https://${escapeHtml(subdomain)}.autoridade.digital" target="_blank" style="
                    flex:1;padding:12px;background:#7c3aed;color:#fff;border-radius:10px;
                    text-decoration:none;text-align:center;font-weight:600;font-size:0.9rem;">
                    🌐 Ver Site
                </a>
                <a href="/api/download/${escapeHtml(subdomain)}" download style="
                    flex:1;padding:12px;background:#0f766e;color:#fff;border-radius:10px;
                    text-decoration:none;text-align:center;font-weight:600;font-size:0.9rem;">
                    📥 Baixar ZIP
                </a>
                <button onclick="closeRelatorio()" style="
                    padding:12px 20px;background:var(--bg);border:1px solid var(--border);
                    border-radius:10px;cursor:pointer;font-family:inherit;color:var(--text);">
                    Fechar
                </button>`;

            document.getElementById('relatorio-modal').style.display = 'flex';
        }

        function closeRelatorio() {
            document.getElementById('relatorio-modal').style.display = 'none';
        }

        async function abrirRelatorio(clienteId, empresaNome) {
            await showRelatorio(clienteId, empresaNome);
        }

        async function deletarCliente(clienteId, empresaNome, subdomain) {
            // Confirmação dupla: digitar o nome do cliente
            const confirmado = prompt(
                `⚠️ Isso vai deletar PERMANENTEMENTE:\n` +
                `  • O cliente "${empresaNome}"\n` +
                `  • Todas as páginas e cache\n` +
                `  • O projeto Pages: ${subdomain}\n` +
                `  • O registro DNS: ${subdomain}.autoridade.digital\n\n` +
                `Para confirmar, digite o nome do cliente exatamente:`
            );
            if (confirmado !== empresaNome) {
                if (confirmado !== null) alert('❌ Nome incorreto. Operação cancelada.');
                return;
            }

            const token = _session?.access_token;
            try {
                const resp = await fetch(`${API_BASE}/api/clientes/${clienteId}`, {
                    method: 'DELETE',
                    headers: { Authorization: `Bearer ${token}` }
                });
                const data = await resp.json();
                if (resp.ok) {
                    const cf = data.cf_results || {};
                    const cfLines = Object.entries(cf).map(([k,v]) => `  ${k}: ${v}`).join('\n');
                    if (data.warnings && data.warnings.length) {
                        alert(
                            `✅ "${empresaNome}" removido do painel.\n\n` +
                            `⚠️ Aviso (Cloudflare):\n` +
                            data.warnings.join('\n') +
                            `\n\nDetalhes CF:\n${cfLines}` +
                            `\n\nVocê pode deletar manualmente no painel Cloudflare Pages.`
                        );
                    } else {
                        alert(`✅ "${empresaNome}" deletado!\n\nResultados CF:\n${cfLines}`);
                    }
                    await loadClientesTab();
                } else {
                    alert('❌ Erro: ' + (data.detail || JSON.stringify(data)));
                }
            } catch(e) {
                alert('❌ Erro de rede: ' + e.message);
            }
        }

        // ── Aba Auditoria ──────────────────────────────────────────────

        async function loadAuditoriaTab() {
            const el = document.getElementById('auditoria-content');
            el.innerHTML = '<div class="empty-state"><div class="spinner" style="margin:0 auto"></div></div>';

            const token = _session?.access_token;
            try {
                const resp = await fetch(`${API_BASE}/api/historico`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (!resp.ok) {
                    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Erro ao carregar histórico</h3></div>`;
                    return;
                }

                const data = await resp.json();
                const historico = data.historico || [];

                if (historico.length === 0) {
                    el.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">💰</div>
                            <h3>Nenhuma geração registrada</h3>
                            <p>O custo de cada geração aparecerá aqui.</p>
                        </div>
                    `;
                    return;
                }

                // Totais
                const totalCostUsd = historico.reduce((s, h) => s + parseFloat(h.cost_usd || 0), 0);
                const totalCostBrl = historico.reduce((s, h) => s + parseFloat(h.cost_brl || 0), 0);
                const totalTokens  = historico.reduce((s, h) => s + parseInt(h.tokens_used || 0), 0);
                const totalPages   = historico.reduce((s, h) => s + parseInt(h.total_pages_generated || 0), 0);

                el.innerHTML = `
                    <div style="overflow-x:auto">
                    <table class="audit-table">
                        <thead>
                            <tr>
                                <th>Data</th>
                                <th>Cliente</th>
                                <th>Páginas</th>
                                <th>Válidas</th>
                                <th>Duração</th>
                                <th>Custo USD</th>
                                <th>Custo BRL</th>
                                <th>Tokens</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${historico.map(h => {
                                const date = new Date(h.created_at).toLocaleDateString('pt-BR');
                                const cliente = h.clientes_perfil?.empresa_nome || h.client_id?.slice(0,8) || '-';
                                // Avoid breaking if h.duration_seconds is somehow missing
                                const durSec = h.duration_seconds || 0;
                                const dur = durSec ? `${Math.floor(durSec/60)}m ${durSec%60}s` : '-';
                                return `
                                    <tr>
                                        <td>${date}</td>
                                        <td>${escapeHtml(cliente)}</td>
                                        <td>${h.total_pages_generated}</td>
                                        <td>${h.valid_pages}</td>
                                        <td>${dur}</td>
                                        <td>$${parseFloat(h.cost_usd).toFixed(4)}</td>
                                        <td>R$${parseFloat(h.cost_brl).toFixed(2)}</td>
                                        <td>${parseInt(h.tokens_used).toLocaleString()}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colspan="2">TOTAL</td>
                                <td>${totalPages}</td>
                                <td>—</td>
                                <td>—</td>
                                <td>$${totalCostUsd.toFixed(4)}</td>
                                <td>R$${totalCostBrl.toFixed(2)}</td>
                                <td>${totalTokens.toLocaleString()}</td>
                            </tr>
                        </tfoot>
                    </table>
                    </div>
                `;
            } catch(e) {
                el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Erro ao carregar histórico</h3></div>`;
            }
        }

        // ── Aba Jobs ───────────────────────────────────────────────────

        async function loadJobsTab() {
            await refreshJobs();
            startJobsPolling();
        }

        async function refreshJobs() {
            const el = document.getElementById('jobs-list');
            const token = _session?.access_token;

            try {
                const resp = await fetch(`${API_BASE}/api/jobs`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (!resp.ok) return;

                const data = await resp.json();
                const jobs = data.jobs || [];

                if (jobs.length === 0) {
                    el.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">⚙️</div>
                            <h3>Nenhum job encontrado</h3>
                            <p>Os jobs de geração aparecerão aqui.</p>
                        </div>
                    `;
                    stopJobsPolling();
                    return;
                }

                el.innerHTML = jobs.map(renderJobRow).join('');

                // Parar polling se não houver jobs ativos
                const hasActive = jobs.some(j => j.status === 'generating' || j.status === 'pending');
                if (!hasActive) stopJobsPolling();
            } catch(e) {
                console.error(e);
            }
        }

        function renderJobRow(j) {
            const date = new Date(j.created_at).toLocaleString('pt-BR', {
                day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit'
            });
            const badgeClass = {
                complete: 'badge-complete', failed: 'badge-failed',
                generating: 'badge-generating', pending: 'badge-pending',
                deploying: 'badge-generating'
            }[j.status] || 'badge-pending';

            const pct = j.progress_pct || 0;
            const stepLabel = j.step || 'queue';
            const errMsg = j.error_message ? `<div style="color:#ef4444;font-size:0.8rem;margin-top:4px">${escapeHtml(j.error_message.slice(0,120))}</div>` : '';

            return `
                <div class="cliente-card" style="margin-bottom:12px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                        <div>
                            <span style="font-size:0.78rem;color:var(--text-muted)">${date}</span>
                            <span style="margin-left:8px;font-size:0.85rem;font-weight:500">${escapeHtml(stepLabel)}</span>
                        </div>
                        <span class="badge ${badgeClass}">${j.status}</span>
                    </div>
                    ${(j.status === 'generating' || j.status === 'deploying') ? `
                        <div class="job-progress">
                            <div class="job-progress-fill" style="width:${pct}%"></div>
                        </div>
                        <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">${pct}%</div>
                    ` : ''}
                    ${errMsg}
                </div>
            `;
        }

        function startJobsPolling() {
            if (_jobsPollingTimer) return;
            _jobsPollingTimer = setInterval(refreshJobs, 3000);
        }

        function stopJobsPolling() {
            if (_jobsPollingTimer) {
                clearInterval(_jobsPollingTimer);
                _jobsPollingTimer = null;
            }
        }

        // ── Aba Sites ──────────────────────────────────────────────

        let _allSites = [];

        async function loadSitesTab() {
            const el = document.getElementById('sites-list');
            el.innerHTML = '<div class="empty-state"><div class="spinner" style="margin:0 auto"></div></div>';

            const token = _session?.access_token;
            try {
                const resp = await fetch(`${API_BASE}/api/sites`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (!resp.ok) {
                    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Erro ao carregar sites</h3></div>`;
                    return;
                }

                const data = await resp.json();
                _allSites = data.sites || [];

                renderSites(_allSites);
            } catch (err) {
                el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Erro ao carregar sites</h3></div>`;
            }
        }

        function filterSites(query) {
            const q = query.toLowerCase().trim();
            if (!q) { renderSites(_allSites); return; }
            const filtered = _allSites.filter(s =>
                (s.empresa_nome || '').toLowerCase().includes(q) ||
                (s.subdomain   || '').toLowerCase().includes(q) ||
                (s.categoria   || '').toLowerCase().includes(q)
            );
            renderSites(filtered);
        }

        function renderSites(sites) {
            const el = document.getElementById('sites-list');

            if (!sites || sites.length === 0) {
                el.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🌐</div>
                        <h3>Nenhum site encontrado</h3>
                        <p>Os sites gerados pelo wizard aparecerão aqui automaticamente.</p>
                    </div>`;
                return;
            }

            el.innerHTML = `
                <div style="overflow-x:auto">
                <table class="audit-table">
                    <thead>
                        <tr>
                            <th>Data</th>
                            <th>Empresa</th>
                            <th>Domínio</th>
                            <th>Categoria</th>
                            <th>Páginas</th>
                            <th>Custo BRL</th>
                            <th>Status</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${sites.map(renderSiteRow).join('')}
                    </tbody>
                </table>
                </div>
                <p style="font-size:0.8rem;color:var(--text-muted);margin-top:12px">
                    ${sites.length} site(s) encontrado(s)
                </p>`;
        }

        function renderSiteRow(s) {
            const date = s.created_at
                ? new Date(s.created_at).toLocaleDateString('pt-BR')
                : '-';
            const badgeClass = s.status === 'live' ? 'badge-live' : 'badge-pending';
            const badgeLabel = s.status === 'live' ? '🟢 Live' : '📦 ZIP';
            const deployUrl  = s.deploy_url || '';
            const zipUrl     = `/api/download/${escapeHtml(s.subdomain)}`;

            return `
                <tr>
                    <td>${date}</td>
                    <td><strong>${escapeHtml(s.empresa_nome)}</strong></td>
                    <td style="font-size:0.82rem;color:var(--text-muted)">${escapeHtml(s.subdomain)}.autoridade.digital</td>
                    <td style="font-size:0.82rem">${escapeHtml(s.categoria || '-')}</td>
                    <td>${s.pages || '-'}</td>
                    <td>R$${parseFloat(s.cost_brl || 0).toFixed(2)}</td>
                    <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
                    <td>
                        <div style="display:flex;gap:6px;flex-wrap:wrap">
                            <a href="${zipUrl}" download
                               style="padding:4px 10px;font-size:0.78rem;border:1px solid var(--border);
                                      border-radius:6px;text-decoration:none;color:var(--text-muted);
                                      white-space:nowrap;">
                               📥 ZIP
                            </a>
                            ${deployUrl ? `
                            <a href="${escapeHtml(deployUrl)}" target="_blank" rel="noopener"
                               style="padding:4px 10px;font-size:0.78rem;background:#7c3aed;
                                      border-radius:6px;text-decoration:none;color:#fff;
                                      white-space:nowrap;">
                               🌐 Ver Site
                            </a>` : ''}
                            <button onclick="openMagicEdit('${escapeHtml(s.id)}', '${escapeHtml(s.empresa_nome)}')" 
                               style="padding:4px 10px;font-size:0.78rem;background:#0f766e;
                                      border:none;border-radius:6px;color:#fff;cursor:pointer;
                                      white-space:nowrap;font-family:inherit;">
                               ✨ Magic Edit
                            </button>
                        </div>
                    </td>
                </tr>`;
        }

        // ── Novo Site (Wizard) logic ──────────────────────────────────
        
        function openNovoSite() {
            // Reset form
            document.getElementById('novo-site-form').reset();
            document.getElementById('ns_cor').value = '#2563EB';
            document.getElementById('ns_cor_picker').value = '#2563EB';
            document.getElementById('ns_horario').value = 'Segunda a Sexta, 8h às 18h';
            document.getElementById('ns_workers').value = '30';
            document.getElementById('ns_theme').value = 'auto';
            
            ns_showStep(1);
            document.getElementById('novo-site-modal').style.display = 'flex';
        }

        function closeNovoSite() {
            document.getElementById('novo-site-modal').style.display = 'none';
        }

        function ns_showStep(step) {
            document.getElementById('step1').style.display = step === 1 ? 'block' : 'none';
            document.getElementById('step2').style.display = step === 2 ? 'block' : 'none';
            document.getElementById('step3').style.display = step === 3 ? 'block' : 'none';
            
            document.getElementById('step1-indicator').style.background = step >= 1 ? 'var(--primary)' : 'var(--border)';
            document.getElementById('step2-indicator').style.background = step >= 2 ? 'var(--primary)' : 'var(--border)';
            document.getElementById('step3-indicator').style.background = step >= 3 ? 'var(--primary)' : 'var(--border)';
        }

        function ns_nextStep(next) {
            // simple validation check before advancing
            if (next === 2) {
                if (!document.getElementById('ns_nome').value || !document.getElementById('ns_categoria').value || !document.getElementById('ns_telefone').value) {
                    alert("Preencha todos os campos obrigatórios da etapa 1.");
                    return;
                }
            }
            if (next === 3) {
                if (!document.getElementById('ns_subdomain').value || !document.getElementById('ns_keywords').value || !document.getElementById('ns_locais').value) {
                    alert("Preencha todos os campos obrigatórios da etapa 2.");
                    return;
                }
            }
            ns_showStep(next);
        }

        function ns_prevStep(prev) {
            ns_showStep(prev);
        }

        async function submitNovoSite() {
            const btn = document.getElementById('ns_submit_btn');
            
            const payload = {
                empresa_nome: document.getElementById('ns_nome').value.trim(),
                categoria: document.getElementById('ns_categoria').value.trim(),
                telefone: document.getElementById('ns_telefone').value.trim(),
                cor_marca: document.getElementById('ns_cor').value.trim(),
                endereco: document.getElementById('ns_endereco').value.trim(),
                horario: document.getElementById('ns_horario').value.trim(),
                subdomain: document.getElementById('ns_subdomain').value.trim(),
                keywords: document.getElementById('ns_keywords').value.split('\n').map(s=>s.trim()).filter(Boolean),
                locais: document.getElementById('ns_locais').value.split('\n').map(s=>s.trim()).filter(Boolean),
                servicos: document.getElementById('ns_servicos').value.split('\n').map(s=>s.trim()).filter(Boolean),
                google_maps_url: document.getElementById('ns_maps').value.trim(),
                theme_mode: document.getElementById('ns_theme').value,
                max_workers: parseInt(document.getElementById('ns_workers').value) || 30
            };

            btn.textContent = 'Aguarde...';
            btn.disabled = true;
            // Render cold-start: mostra hint após 4s
            const _coldHint = setTimeout(() => {
                if (btn.disabled) btn.textContent = 'Iniciando servidor... ⏳ aguarde';
            }, 4000);

            const token = _session?.access_token;
            try {
                const resp = await fetch(`${API_BASE}/api/clientes`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await resp.json();
                clearTimeout(_coldHint);
                if (resp.ok) {
                    closeNovoSite();
                    openProgressModal(data.job_id, data.cliente_id, payload.empresa_nome);
                } else {
                    alert('\u274c Erro: ' + (data.detail || JSON.stringify(data)));
                    btn.textContent = '\ud83d\ude80 Iniciar Gera\u00e7\u00e3o';
                    btn.disabled = false;
                }
            } catch (err) {
                clearTimeout(_coldHint);
                alert('\u274c Erro de rede: ' + err.message);
                btn.textContent = '\ud83d\ude80 Iniciar Gera\u00e7\u00e3o';
                btn.disabled = false;
            }
        }

        // ── Magic Edit Modal ─────────────────────────────────────────


        let _magicEditSiteId = null;
        let _magicEditType = 'site'; // 'site' ou 'cliente'

        function openMagicEdit(id, empresaNome, type = 'site') {
            _magicEditSiteId = id;
            _magicEditType = type;
            document.getElementById('magic-edit-title').textContent = `✨ Magic Edit — ${empresaNome}`;
            document.getElementById('magic-edit-instruction').value = '';
            document.getElementById('magic-edit-result').style.display = 'none';
            document.getElementById('magic-edit-result').innerHTML = '';
            document.getElementById('magic-edit-modal').style.display = 'flex';
            document.getElementById('magic-edit-instruction').focus();
        }

        function closeMagicEdit() {
            document.getElementById('magic-edit-modal').style.display = 'none';
            _magicEditSiteId = null;
        }

        async function submitMagicEdit() {
            const instruction = document.getElementById('magic-edit-instruction').value.trim();
            if (!instruction) { alert('Digite uma instrução'); return; }

            const btn = document.getElementById('magic-edit-btn');
            const resultEl = document.getElementById('magic-edit-result');
            btn.textContent = 'Processando...';
            btn.disabled = true;
            resultEl.style.display = 'none';

            const token = _session?.access_token;
            try {
                const endpoint = _magicEditType === 'cliente' 
                    ? `${API_BASE}/api/clientes/${_magicEditSiteId}/chat-edit`
                    : `${API_BASE}/api/sites/${_magicEditSiteId}/magic-edit`;

                const resp = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ instruction })
                });

                const data = await resp.json();

                if (resp.ok) {
                    resultEl.style.display = 'block';
                    resultEl.style.color = '#10b981';
                    
                    if (_magicEditType === 'cliente') {
                        if (data.job_id) {
                            const tier = data.edit_type === 'tier_1.5_fast_sync' ? '⚡ Fast Sync' : '🔄 Regeração Completa';
                            resultEl.innerHTML = `✅ Edição aplicada! ${tier} iniciado (ID: ${data.job_id}). Acompanhe na aba Jobs.`;
                            switchTab('jobs');
                        } else {
                            resultEl.innerHTML = `ℹ️ Nenhuma alteração detectada pelo editor. Use o botão <strong>⚡ Redeploy</strong> para republicar sem mudanças.`;
                        }
                        await loadClientesTab();
                    } else {
                        resultEl.innerHTML = `
                            ✅ ${data.message}<br>
                            ${data.deploy_url ? `🌐 <a href="${data.deploy_url}" target="_blank" style="color:#00b4d8">${data.deploy_url}</a>` : ''}
                        `;
                        await loadSitesTab();
                    }
                } else {
                    resultEl.style.display = 'block';
                    resultEl.style.color = '#ef4444';
                    resultEl.textContent = '❌ Erro: ' + (data.detail || JSON.stringify(data));
                }
            } catch(err) {
                resultEl.style.display = 'block';
                resultEl.style.color = '#ef4444';
                resultEl.textContent = '❌ Erro de rede: ' + err.message;
            } finally {
                btn.textContent = '✨ Aplicar';
                btn.disabled = false;
            }
        }

function showLoading() {
            document.getElementById('loading').style.display = 'flex';
            const loginEl = document.getElementById('login');
            if (loginEl) loginEl.style.display = 'none';
            document.getElementById('dashboard').style.display = 'none';
        }

        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }

        
        function showDashboard() {
            document.getElementById('dashboard').style.display = 'flex';
        }

        function renderCards(leads) {
            const cardsContainer = document.getElementById('cards');
            cardsContainer.innerHTML = '';

            const totalLeads = leads.length;

            const now = new Date();
            const thisMonth = new Date(now.getFullYear(), now.getMonth(), 1);
            const thisWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

            const monthLeads = leads.filter(lead => new Date(lead.created_at) >= thisMonth).length;
            const weekLeads = leads.filter(lead => new Date(lead.created_at) >= thisWeek).length;

            const cardsData = [
                { label: 'Total de Leads', value: totalLeads },
                { label: 'Este Mês', value: monthLeads },
                { label: 'Esta Semana', value: weekLeads }
            ];

            cardsData.forEach(card => {
                const cardElement = document.createElement('div');
                cardElement.className = 'card';
                cardElement.innerHTML = `
                    <div class="card-value">${card.value}</div>
                    <div class="card-label">${card.label}</div>
                `;
                cardsContainer.appendChild(cardElement);
            });

            // Update subtitle with domain if available
            const subtitleEl = document.querySelector('.header-subtitle');
            if (subtitleEl && leads.length > 0 && leads[0].dominio) {
                subtitleEl.textContent = `Dashboard de Leads — ${leads[0].dominio}`;
            }
        }

        function renderRanking(leads) {
            const rankingContainer = document.getElementById('ranking');

            if (leads.length === 0) {
                rankingContainer.innerHTML = '';
                return;
            }

            const keywordCounts = leads.reduce((acc, lead) => {
                const keyword = lead.keyword || 'Não especificado';
                acc[keyword] = (acc[keyword] || 0) + 1;
                return acc;
            }, {});

            const sortedKeywords = Object.entries(keywordCounts)
                .sort((a, b) => b[1] - a[1]);

            const maxCount = sortedKeywords.length > 0 ? sortedKeywords[0][1] : 1;

            let rankingHTML = `
                <h2>Leads por Palavra-chave</h2>
                <table class="ranking-table">
                    <thead>
                        <tr>
                            <th>Palavra-chave</th>
                            <th>Quantidade</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            sortedKeywords.forEach(([keyword, count]) => {
                const percentage = (count / maxCount) * 100;
                rankingHTML += `
                    <tr>
                        <td>${escapeHtml(keyword)}</td>
                        <td>${count}</td>
                        <td>
                            <div class="ranking-bar-container">
                                <div class="ranking-bar" style="width: ${percentage}%"></div>
                            </div>
                        </td>
                    </tr>
                `;
            });

            rankingHTML += `
                    </tbody>
                </table>
            `;

            rankingContainer.innerHTML = rankingHTML;
        }

        function renderTable(leads) {
            const tableContainer = document.getElementById('leads-table');

            if (leads.length === 0) {
                tableContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <h3>Nenhum lead capturado ainda</h3>
                        <p>Os leads aparecerão aqui assim que visitantes interagirem com o widget de WhatsApp.</p>
                    </div>
                `;
                return;
            }

            const displayLeads = leads.slice(0, 50);
            const showNote = leads.length > 50;

            let tableHTML = `
                <h2>Todos os Leads</h2>
                <div class="leads-table-container">
                    <table class="leads-table">
                        <thead>
                            <tr>
                                <th>Data</th>
                                <th>Nome</th>
                                <th>WhatsApp</th>
                                <th>Palavra-chave</th>
                                <th>Local</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            displayLeads.forEach(lead => {
                const date = new Date(lead.created_at).toLocaleString('pt-BR', {
                    timeZone: 'America/Sao_Paulo',
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });

                tableHTML += `
                    <tr>
                        <td>${date}</td>
                        <td>${escapeHtml(lead.nome)}</td>
                        <td>${escapeHtml(lead.whatsapp)}</td>
                        <td>${escapeHtml(lead.keyword)}</td>
                        <td>${escapeHtml(lead.local)}</td>
                    </tr>
                `;
            });

            tableHTML += `
                        </tbody>
                    </table>
                </div>
            `;

            if (showNote) {
                tableHTML += `<p style="margin-top: 16px; font-size: 0.875rem; color: var(--text-muted);">Exibindo os 50 leads mais recentes</p>`;
            }

            tableContainer.innerHTML = tableHTML;
        }

        function updateFooter() {
            const year = new Date().getFullYear();
            document.querySelector('footer').innerHTML = `SiteGen © ${year}`;
        }

        function initTheme() {
            const saved = localStorage.getItem('as-theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const isDark = saved ? saved === 'dark' : prefersDark;
            applyTheme(isDark ? 'dark' : 'light');

            document.getElementById('theme-toggle').addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                applyTheme(next);
                localStorage.setItem('as-theme', next);
            });
        }

        function applyTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            const btn = document.getElementById('theme-toggle');
            if (btn) btn.textContent = theme === 'dark' ? '☀️ Claro' : '🌙 Escuro';
        }

        
        document.addEventListener('DOMContentLoaded', () => {
            initTheme();
            init();
            updateFooter();
        });
