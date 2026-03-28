/**
 * Autoridade Sites - Main JS
 * Scroll animations, mobile menu, header effects
 */
(function() {
    'use strict';

    // Header scroll effect
    const header = document.querySelector('.site-header');
    if (header) {
        window.addEventListener('scroll', () => {
            header.classList.toggle('scrolled', window.scrollY > 50);
        }, { passive: true });
    }

    // Mobile menu toggle
    const toggle = document.querySelector('.mobile-toggle');
    const nav = document.querySelector('.header-nav');
    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            nav.classList.toggle('open');
            toggle.innerHTML = nav.classList.contains('open')
                ? '<i class="fas fa-times"></i>'
                : '<i class="fas fa-bars"></i>';
        });
        nav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                nav.classList.remove('open');
                toggle.innerHTML = '<i class="fas fa-bars"></i>';
            });
        });
    }

    // Scroll reveal animation
    const reveals = document.querySelectorAll('.reveal');
    if (reveals.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

        reveals.forEach(el => observer.observe(el));
    }

    // Injetar dados dinâmicos do dados.js se disponível
    if (typeof DadosSite !== 'undefined') {
        const preencherDadosDinamicos = () => {
            // Textos
            document.querySelectorAll('[data-dinamico]').forEach(el => {
                const chave = el.getAttribute('data-dinamico');
                if (DadosSite[chave]) {
                    el.textContent = DadosSite[chave];
                }
            });
            // Hrefs (Links, ex: WhatsApp)
            document.querySelectorAll('[data-dinamico-href]').forEach(el => {
                const chave = el.getAttribute('data-dinamico-href');
                if (DadosSite[chave]) {
                    el.setAttribute('href', DadosSite[chave]);
                }
            });
            // Google Maps
            document.querySelectorAll('iframe[data-dinamico-src]').forEach(el => {
                const chave = el.getAttribute('data-dinamico-src');
                if (DadosSite[chave]) {
                    el.setAttribute('src', DadosSite[chave]);
                }
            });
        };
        
        const renderizarServicos = () => {
            const servicosContainer = document.getElementById('dynamico-servicos');
            if (servicosContainer && typeof _DADOS_SERVICOS !== 'undefined' && _DADOS_SERVICOS.length > 0) {
                let html = '';
                _DADOS_SERVICOS.forEach(srv => {
                    html += `
                        <div class="service-card reveal visible">
                            <div class="service-icon"><i class="${srv.icone || 'fas fa-check'}"></i></div>
                            <h3>${srv.titulo}</h3>
                            <p>${srv.descricao}</p>
                        </div>
                    `;
                });
                servicosContainer.innerHTML = html;
                document.getElementById('servicos').style.display = 'block';
            }
        };

        const initDynamicData = () => {
            preencherDadosDinamicos();
            renderizarServicos();
        };
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initDynamicData);
        } else {
            initDynamicData();
        }
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
})();
