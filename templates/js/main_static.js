/**
 * Autoridade Sites — Main Static JS
 *
 * Versão minimalista para o template estático (index_static.html).
 * Os dados do site já estão no HTML gerado pelo Python —
 * NÃO há injeção de conteúdo via dados.js nem via _DADOS_SERVICOS.
 *
 * Responsabilidades:
 *   - Header com efeito de scroll
 *   - Mobile menu (hamburguer)
 *   - Hero parallax suave
 *   - Scroll reveal via IntersectionObserver
 *   - Smooth scroll para âncoras internas
 */
(function () {
    'use strict';

    // ── Header scroll effect ──────────────────────────────────────────────────
    var header = document.querySelector('.site-header');
    if (header) {
        window.addEventListener('scroll', function () {
            header.classList.toggle('scrolled', window.scrollY > 60);
        }, { passive: true });
    }

    // ── Hero parallax ─────────────────────────────────────────────────────────
    var heroBg = document.querySelector('.hero-bg-image');
    if (heroBg) {
        window.addEventListener('scroll', function () {
            if (window.scrollY < window.innerHeight) {
                heroBg.style.backgroundPositionY = (window.scrollY * 0.35) + 'px';
            }
        }, { passive: true });
    }

    // ── Mobile menu toggle ────────────────────────────────────────────────────
    var toggle = document.querySelector('.mobile-toggle');
    var nav = document.querySelector('.header-nav');
    if (toggle && nav) {
        toggle.addEventListener('click', function () {
            var isOpen = nav.classList.toggle('open');
            toggle.innerHTML = isOpen
                ? '<i class="fas fa-times"></i>'
                : '<i class="fas fa-bars"></i>';
            document.body.style.overflow = isOpen ? 'hidden' : '';
        });
        // Fechar menu ao clicar em qualquer link da nav
        nav.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                nav.classList.remove('open');
                toggle.innerHTML = '<i class="fas fa-bars"></i>';
                document.body.style.overflow = '';
            });
        });
    }

    // ── Scroll reveal via IntersectionObserver ────────────────────────────────
    var reveals = document.querySelectorAll('.reveal');
    if (reveals.length > 0 && 'IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -50px 0px' });

        reveals.forEach(function (el) { observer.observe(el); });
    } else {
        // Fallback para browsers sem IntersectionObserver: mostrar tudo
        reveals.forEach(function (el) { el.classList.add('visible'); });
    }

    // ── Smooth scroll para âncoras ────────────────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var targetSel = this.getAttribute('href');
            if (targetSel === '#') return;
            var target = document.querySelector(targetSel);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

})();
