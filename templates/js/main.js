/**
 * Autoridade Sites — Main JS (Premium)
 * Scroll animations, mobile menu, header effects, hero parallax
 */
(function() {
    'use strict';

    // === Header scroll effect ===
    const header = document.querySelector('.site-header');
    if (header) {
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            const scrollY = window.scrollY;
            header.classList.toggle('scrolled', scrollY > 60);
            lastScroll = scrollY;
        }, { passive: true });
    }

    // === Hero parallax ===
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', () => {
            const scrollY = window.scrollY;
            if (scrollY < window.innerHeight) {
                hero.style.backgroundPositionY = `${scrollY * 0.35}px`;
            }
        }, { passive: true });
    }

    // === Mobile menu toggle ===
    const toggle = document.querySelector('.mobile-toggle');
    const nav = document.querySelector('.header-nav');
    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            const isOpen = nav.classList.toggle('open');
            toggle.innerHTML = isOpen
                ? '<i class="fas fa-times"></i>'
                : '<i class="fas fa-bars"></i>';
            document.body.style.overflow = isOpen ? 'hidden' : '';
        });
        nav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                nav.classList.remove('open');
                toggle.innerHTML = '<i class="fas fa-bars"></i>';
                document.body.style.overflow = '';
            });
        });
    }

    // === Scroll reveal animation ===
    const reveals = document.querySelectorAll('.reveal');
    if (reveals.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -50px 0px' });

        reveals.forEach(el => observer.observe(el));
    }

    // === Dynamic data injection from dados.js ===
    if (typeof DadosSite !== 'undefined') {
        const preencherDadosDinamicos = () => {
            // Text content
            document.querySelectorAll('[data-dinamico]').forEach(el => {
                const chave = el.getAttribute('data-dinamico');
                if (DadosSite[chave]) {
                    el.textContent = DadosSite[chave];
                }
            });
            // Links (href)
            document.querySelectorAll('[data-dinamico-href]').forEach(el => {
                const chave = el.getAttribute('data-dinamico-href');
                if (DadosSite[chave]) {
                    el.setAttribute('href', DadosSite[chave]);
                }
            });
            // Google Maps iframe
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
                const servicosSection = document.getElementById('servicos');
                if (servicosSection) servicosSection.style.display = 'block';
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

    // === Smooth scroll for anchor links ===
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
