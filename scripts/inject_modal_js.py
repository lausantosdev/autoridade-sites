# -*- coding: utf-8 -*-
"""Injeta o bloco de JS dos modais de Progresso e Relatório no dashboard/index.html"""

JS_BLOCK = r"""
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
        async function showRelatorio(clienteId, empresaNome) {
            const token = _session?.access_token;
            try {
                const r = await fetch(`${API_BASE}/api/clientes/${clienteId}/ultimo-relatorio`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (!r.ok) return;
                const rel = await r.json();
                _renderRelatorio(rel, clienteId, empresaNome);
            } catch(e) { console.warn('Relatório:', e); }
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

"""

ANCHOR = b'        async function deletarCliente('

with open('dashboard/index.html', 'rb') as f:
    content = f.read()

if ANCHOR not in content:
    print('ERRO: anchor nao encontrado')
else:
    idx = content.index(ANCHOR)
    # Insert JS block right before deletarCliente
    content2 = content[:idx] + JS_BLOCK.encode('utf-8') + content[idx:]
    with open('dashboard/index.html', 'wb') as f:
        f.write(content2)
    print('OK - JS dos modais injetado antes de deletarCliente')
