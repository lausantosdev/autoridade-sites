/**
 * Autoridade Sites — Lead Capture Form Handler
 * 
 * Fluxo: Form submit → POST Worker (se configurado) → WhatsApp redirect
 * 
 * Configuração esperada em window.AUTORIDADE_WIDGET:
 *   workerUrl, clientToken, dominio, empresaNome, whatsappNumero, keyword, local
 */
(function() {
    'use strict';

    var form = document.getElementById('lead-form');
    if (!form) return;

    var config = window.AUTORIDADE_WIDGET || {};

    // ===== 0. Mensagem de erro reutilizável =====
    var errorMsg = document.createElement('p');
    errorMsg.className = 'lead-form-error';
    errorMsg.textContent = '';
    errorMsg.style.display = 'none';

    // Inserir após os campos, antes do botão
    var btnEl = form.querySelector('.btn-whatsapp');
    if (btnEl) {
        form.insertBefore(errorMsg, btnEl);
    } else {
        form.appendChild(errorMsg);
    }

    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = 'block';
        // Auto-esconder após 4s
        clearTimeout(errorMsg._timer);
        errorMsg._timer = setTimeout(function() {
            errorMsg.style.display = 'none';
        }, 4000);
    }

    function hideError() {
        errorMsg.style.display = 'none';
        clearTimeout(errorMsg._timer);
    }

    // Limpar erro ao digitar
    var nomeInput = form.querySelector('[name="nome"]');
    var whatsappInput = form.querySelector('[name="whatsapp"]');

    function onInputChange() {
        // Limpar estado de erro dos campos
        if (nomeInput) nomeInput.classList.remove('input-error');
        if (whatsappInput) whatsappInput.classList.remove('input-error');
        hideError();
    }

    if (nomeInput) nomeInput.addEventListener('input', onInputChange);
    if (whatsappInput) whatsappInput.addEventListener('input', onInputChange);

    // ===== 1. Form submit handler =====
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        var nome = nomeInput ? nomeInput.value.trim() : '';
        var whatsapp = whatsappInput ? whatsappInput.value.trim() : '';

        // Validar campos vazios — mostrar erro visual
        if (!nome && !whatsapp) {
            if (nomeInput) nomeInput.classList.add('input-error');
            if (whatsappInput) whatsappInput.classList.add('input-error');
            showError('Preencha seu nome e WhatsApp para continuar.');
            if (nomeInput) nomeInput.focus();
            return;
        }
        if (!nome) {
            if (nomeInput) nomeInput.classList.add('input-error');
            showError('Preencha seu nome para continuar.');
            nomeInput.focus();
            return;
        }
        if (!whatsapp) {
            if (whatsappInput) whatsappInput.classList.add('input-error');
            showError('Preencha seu WhatsApp para continuar.');
            whatsappInput.focus();
            return;
        }

        // Validar WhatsApp (mínimo 8 dígitos)
        var digits = whatsapp.replace(/\D/g, '');
        if (digits.length < 8) {
            if (whatsappInput) whatsappInput.classList.add('input-error');
            showError('Informe um número de WhatsApp válido.');
            whatsappInput.focus();
            return;
        }

        hideError();

        // Feedback visual
        var btn = form.querySelector('button[type="submit"]');
        var originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fab fa-whatsapp"></i> Abrindo WhatsApp...';

        // POST para Worker (se configurado — fire-and-forget)
        if (config.workerUrl) {
            var keywordField = form.querySelector('[name="keyword"]');
            var localField = form.querySelector('[name="local"]');

            fetch(config.workerUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nome: nome,
                    whatsapp: whatsapp,
                    dominio: config.dominio || window.location.hostname,
                    pagina: window.location.pathname,
                    keyword: keywordField ? keywordField.value : (config.keyword || ''),
                    local: localField ? localField.value : (config.local || ''),
                    client_token: config.clientToken || ''
                })
            }).catch(function() { /* silencioso */ });
        }

        // Montar mensagem pré-preenchida para WhatsApp
        var keyword = config.keyword || '';
        var local = config.local || '';
        var contexto = '';
        if (keyword && local) {
            contexto = ' Vi o site sobre ' + keyword + ' em ' + local + ' e';
        }
        var msg = 'Olá, sou ' + nome + '.' + contexto +
                  ' gostaria de saber mais sobre os serviços.';

        var waUrl = 'https://wa.me/' + (config.whatsappNumero || '') +
                    '?text=' + encodeURIComponent(msg);

        // Abrir WhatsApp
        window.open(waUrl, '_blank');

        // Reset após 2s
        setTimeout(function() {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
            form.reset();
        }, 2000);
    });

    // ===== 2. Smooth scroll para âncoras #contato =====
    function setupSmoothScroll(link) {
        if (link.dataset.awScroll) return;
        link.dataset.awScroll = '1';
        link.addEventListener('click', function(e) {
            var target = document.getElementById('contato');
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    // Links estáticos #contato
    document.querySelectorAll('a[href="#contato"]').forEach(setupSmoothScroll);

    // ===== 3. Observer para React: redireciona links wa.me dinâmicos =====
    function redirectDynamicWaLinks() {
        document.querySelectorAll('a[href*="wa.me"]:not([data-aw-redirect])').forEach(function(link) {
            link.dataset.awRedirect = '1';
            
            // Força o comportamento de ancora na mesma página
            link.removeAttribute('target');
            link.href = '#contato';
            
            link.addEventListener('click', function(e) {
                e.preventDefault();
                var target = document.getElementById('contato');
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

    redirectDynamicWaLinks();

    // MutationObserver para capturar links criados pelo React
    if (typeof MutationObserver !== 'undefined') {
        var observer = new MutationObserver(redirectDynamicWaLinks);
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // Safety net
    setTimeout(redirectDynamicWaLinks, 500);
    setTimeout(redirectDynamicWaLinks, 1500);
})();
