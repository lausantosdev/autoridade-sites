"""
Template Injector — Injeta dados do site no template SiteGen pré-buildado.

Pega o dist/index.html (build único do template) e injeta:
1. window.__SITE_DATA__ (dados do site em JSON)
2. Meta tags SEO (<title>, <meta>, og:tags)
3. Schema JSON-LD (LocalBusiness + FAQPage)
4. Copia assets (JS/CSS bundled + hero image) para o output

Output: um index.html completo com design premium SiteGen + dados do cliente.
"""
import os
import json
import shutil
from core.logger import get_logger
from core.exceptions import TemplateError
logger = get_logger(__name__)


# Caminho padrão do dist/ commitado no repo
TEMPLATE_DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'template-dist')


def inject_template(
    site_data: dict,
    output_dir: str,
    dist_dir: str = None,
    hero_image_path: str = None,
) -> str:
    """
    Injeta os dados do site no template SiteGen pré-buildado.
    
    Args:
        site_data: dict compliant com SiteData (gerado por site_data_builder)
        output_dir: diretório de saída (ex: output/cleanproestofados.com.br/)
        dist_dir: caminho do dist/ SiteGen (default: template-dist/ no repo)
        hero_image_path: caminho da hero image gerada (copiada para output)
        
    Returns:
        Caminho do index.html gerado
    """
    dist_dir = dist_dir or TEMPLATE_DIST_DIR
    dist_index = os.path.join(dist_dir, 'index.html')
    
    if not os.path.exists(dist_index):
        raise TemplateError(
            f"Template SiteGen não encontrado em {dist_index}. "
            f"Execute 'npm run build' na pasta do template e copie o dist/ para template-dist/."
        )
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Ler o template pré-buildado
    with open(dist_index, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 2. Injetar meta tags SEO
    html = _inject_meta_tags(html, site_data)
    
    # 3. Injetar Schema JSON-LD
    html = _inject_schema(html, site_data)
    
    # 4. Injetar window.__SITE_DATA__ (o principal)
    html = _inject_site_data(html, site_data)
    
    # 4.1 Injetar script de footer links SEO
    html = _inject_footer_links_script(html)
    
    # 4.2 Injetar formulário de captura de leads
    html = _inject_leads_form(html, site_data)
    
    # 5. Copiar assets (JS/CSS bundles)
    _copy_assets(dist_dir, output_dir)
    
    # 6. Copiar hero image se fornecida (e se não for o mesmo arquivo)
    if hero_image_path and os.path.exists(hero_image_path):
        dest = os.path.join(output_dir, 'hero-image.webp')
        if os.path.abspath(hero_image_path) != os.path.abspath(dest):
            shutil.copy2(hero_image_path, dest)
    
    # 7. Copiar favicon
    favicon_src = os.path.join(dist_dir, 'favicon.svg')
    if os.path.exists(favicon_src):
        shutil.copy2(favicon_src, os.path.join(output_dir, 'favicon.svg'))
    
    # 8. Salvar o index.html final
    output_path = os.path.join(output_dir, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info("Home page SiteGen gerada: %s", output_path)
    return output_path


def _inject_meta_tags(html: str, site_data: dict) -> str:
    """Substitui os marcadores de meta tags pelos valores reais e injeta tags SEO ausentes."""
    seo = site_data.get('seo', {})
    theme = site_data.get('theme', {})
    empresa = site_data.get('empresa', {})
    dominio = empresa.get('dominio', '')
    canonical_url = f"https://{dominio}/" if dominio else ''

    replacements = {
        '__SITE_TITLE__': seo.get('title', ''),
        '__SITE_META_DESC__': seo.get('metaDescription', ''),
        '__SITE_META_KEYWORDS__': seo.get('metaKeywords', ''),
        '__SITE_OG_TITLE__': seo.get('ogTitle', seo.get('title', '')),
        '__SITE_OG_DESC__': seo.get('ogDescription', seo.get('metaDescription', '')),
        '__SITE_THEME_COLOR__': theme.get('color', '#000000'),
        '__SITE_THEME_MODE__': theme.get('mode', 'dark'),
    }

    for marker, value in replacements.items():
        html = html.replace(marker, _escape_html_attr(str(value)))

    # Injetar preload da hero image (LCP otimizado para PageSpeed)
    hero_preload = '\n    <link rel="preload" as="image" href="./hero-image.webp" type="image/webp" fetchpriority="high">'

    # Injetar canonical, og:url e robots antes do </head>
    extra_tags = (
        f'\n    <link rel="canonical" href="{canonical_url}">'
        f'\n    <meta property="og:url" content="{canonical_url}">'
        f'\n    <meta name="robots" content="index, follow">'
    )
    html = html.replace('</head>', hero_preload + extra_tags + '\n</head>', 1)

    return html


def _inject_schema(html: str, site_data: dict) -> str:
    """Injeta os blocos de Schema JSON-LD no <head>."""
    schema = site_data.get('schema', {})
    blocks = []
    
    # LocalBusiness
    lb = schema.get('localBusiness', '')
    if lb:
        # Formatar para legibilidade
        try:
            lb_obj = json.loads(lb) if isinstance(lb, str) else lb
            lb_formatted = json.dumps(lb_obj, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            lb_formatted = lb
        blocks.append(f'<script type="application/ld+json">\n{lb_formatted}\n</script>')
    
    # FAQPage
    faq = schema.get('faqPage', '')
    if faq:
        try:
            faq_obj = json.loads(faq) if isinstance(faq, str) else faq
            faq_formatted = json.dumps(faq_obj, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            faq_formatted = faq
        blocks.append(f'<script type="application/ld+json">\n{faq_formatted}\n</script>')
    
    schema_html = '\n    '.join(blocks) if blocks else ''
    return html.replace('<!-- SCHEMA_INJECT -->', schema_html)


def _inject_site_data(html: str, site_data: dict) -> str:
    """Injeta o objeto SiteData como window.__SITE_DATA__ via <script>."""
    # Serializar o JSON de forma compacta (sem indentação) para produção
    json_str = json.dumps(site_data, ensure_ascii=False, separators=(',', ':'))
    
    # Escapar </script> dentro do JSON (caso algum valor contenha)
    json_str = json_str.replace('</script>', '<\\/script>')
    
    script_tag = f'<script>window.__SITE_DATA__={json_str}</script>'
    return html.replace('<!-- SITE_DATA_INJECT -->', script_tag)


def _inject_footer_links_script(html: str) -> str:
    """Injeta micro-script que transforma textos do footer em links SEO após o React renderizar."""
    script = """
<script>
(function() {
  function linkifyFooter() {
    var d = window.__SITE_DATA__;
    if (!d || !d.footer || !d.footer.slugMap) return;
    var map = d.footer.slugMap;
    var footer = document.querySelector('footer');
    if (!footer) return;
    var cols = footer.querySelectorAll('div');
    cols.forEach(function(col) {
      var h = col.querySelector('h4');
      if (!h) return;
      var label = h.textContent.trim().toLowerCase();
      var slugObj = null;
      var titlePrefix = '';
      if (label.indexOf('servi') > -1 && map.servicos) {
        slugObj = map.servicos;
        titlePrefix = '{srv} em ' + (d.seo && d.seo.local ? d.seo.local : '');
      }
      // Áreas Atendidas: itens exibidos como texto puro, sem links
      if (!slugObj) return;
      var items = col.querySelectorAll('span, p');
      items.forEach(function(el) {
        var txt = el.textContent.trim();
        if (slugObj[txt]) {
          var a = document.createElement('a');
          a.href = slugObj[txt];
          a.title = titlePrefix.indexOf('{srv}') > -1
            ? titlePrefix.replace('{srv}', txt)
            : titlePrefix.replace('{city}', txt);
          a.textContent = el.textContent;
          a.style.cssText = el.style.cssText;
          a.className = el.className;
          el.parentNode.replaceChild(a, el);
        }
      });
    });
  }
  if (document.readyState === 'complete') {
    setTimeout(linkifyFooter, 500);
  } else {
    window.addEventListener('load', function() {
      setTimeout(linkifyFooter, 500);
    });
  }
})();
</script>"""
    return html.replace('</body>', script + '\n</body>')


def _inject_leads_form(html: str, site_data: dict) -> str:
    """Injeta o formulário de Captura de Leads na Home Premium."""
    # 1. CSS — link externo (widget.css é copiado pelo output_builder junto com /css)
    html = html.replace('</head>', '<link rel="stylesheet" href="css/widget.css?v=2">\n</head>', 1)

    # SVG inline do WhatsApp — zero dependência de CDN/FontAwesome
    _WA_ICON = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" '
        'width="20" height="20" aria-hidden="true" style="vertical-align:middle;flex-shrink:0;">'
        '<path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15'
        '-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475'
        '-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52'
        '.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207'
        '-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372'
        '-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2'
        ' 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085'
        ' 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347'
        'm-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648'
        '-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0'
        ' 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884'
        '-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892'
        'c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448'
        'h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/>'
        '</svg>'
    )
        
    # 2. Dados
    mega_cta = site_data.get('megaCtaSection', {})
    cta_titulo = mega_cta.get('title', 'Pronto para começar?')
    cta_subtitulo = mega_cta.get('subtitle', 'Entre em contato agora e fale com nossa equipe sem compromisso.')
    
    leads = site_data.get('leads', {})
    worker_url = leads.get('workerUrl', '')
    client_token = leads.get('clientToken', '')
    
    empresa = site_data.get('empresa', {})
    dominio = empresa.get('dominio', '')
    empresa_nome = empresa.get('nome', '')
    whatsapp_num = empresa.get('telefoneWhatsapp', '')
    
    seo = site_data.get('seo', {})
    keyword = seo.get('keyword', '')
    local = seo.get('local', '')
    cor_marca = site_data.get('theme', {}).get('color', '#6366f1')
    
    # 3. HTML Form e CSS Inline para o container (seção oculta inicialmente)
    form_html = f"""
    <style>
    /* Oculta botões wa.me em todas as seções EXCETO a Hero (primeira) */
    /* O botão do Hero é redirecionado para #contato via JS */
    #root section:not(:first-of-type) a[href*="wa.me"] {{
      display: none !important;
    }}
    /* ═══ Seção Fale Conosco — Premium Injected ═══ */
    #contato {{
      display: none; /* Oculto até o integrador posicionar */
      padding: 96px 0 80px;
      width: 100%;
      scroll-margin-top: 100px;
      background: linear-gradient(
        180deg,
        color-mix(in srgb, {cor_marca} 8%, transparent) 0%,
        color-mix(in srgb, {cor_marca} 14%, transparent) 50%,
        color-mix(in srgb, {cor_marca} 8%, transparent) 100%
      );
      border-top: 1px solid color-mix(in srgb, {cor_marca} 15%, transparent);
      border-bottom: 1px solid color-mix(in srgb, {cor_marca} 15%, transparent);
    }}
    #contato .container {{
      max-width: 640px;
      margin: 0 auto;
      padding: 0 24px;
      text-align: center;
    }}
    /* Eyebrow badge */
    #contato .cta-eyebrow {{
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--muted-foreground, #64748b);
      margin-bottom: 16px;
    }}
    #contato .cta-title {{
      font-size: 2.25rem;
      font-weight: 800;
      margin-bottom: 16px;
      color: var(--foreground, #0f172a);
      letter-spacing: -0.025em;
      line-height: 1.2;
    }}
    #contato .cta-subtitle {{
      font-size: 0.95rem;
      color: var(--muted-foreground, #64748b);
      margin-bottom: 36px;
      line-height: 1.7;
      max-width: 480px;
      margin-left: auto;
      margin-right: auto;
    }}

    /* ═══ Dark theme ═══ */
    html[data-theme="dark"] #contato,
    [data-theme="dark"] #contato {{
      background: linear-gradient(
        180deg,
        color-mix(in srgb, {cor_marca} 6%, transparent) 0%,
        color-mix(in srgb, {cor_marca} 10%, transparent) 50%,
        color-mix(in srgb, {cor_marca} 6%, transparent) 100%
      );
      border-top-color: color-mix(in srgb, {cor_marca} 12%, transparent);
      border-bottom-color: color-mix(in srgb, {cor_marca} 12%, transparent);
    }}
    html[data-theme="dark"] #contato .cta-eyebrow,
    [data-theme="dark"] #contato .cta-eyebrow {{
      color: rgba(255, 255, 255, 0.45);
    }}
    html[data-theme="dark"] #contato .cta-title,
    [data-theme="dark"] #contato .cta-title {{
      color: var(--foreground, #e2e8f0);
    }}
    html[data-theme="dark"] #contato .cta-subtitle,
    [data-theme="dark"] #contato .cta-subtitle {{
      color: rgba(255, 255, 255, 0.55);
    }}

    /* ═══ Mobile ═══ */
    @media (max-width: 768px) {{
      #contato {{
        padding: 64px 0 56px;
      }}
      #contato .cta-title {{
        font-size: 1.75rem;
      }}
    }}

    /* ═══ Bottom CTA (reforço pré-footer) ═══ */
    #bottom-cta {{
      display: none;
      padding: 24px 0 80px 0; /* Padding top leve, compensando o bottom da seção anterior */
      width: 100%;
      text-align: center;
    }}
    #bottom-cta .bottom-cta-card {{
      max-width: 480px;
      margin: 0 auto;
      padding: 40px 32px;
      border-radius: 20px;
      background: linear-gradient(135deg, {cor_marca}18 0%, {cor_marca}28 100%);
      border: 1px solid {cor_marca}22;
    }}
    #bottom-cta .bottom-cta-text {{
      font-size: 1rem;
      font-weight: 500;
      color: #1e293b;
      line-height: 1.7;
      margin-bottom: 24px;
    }}
    #bottom-cta .bottom-cta-text strong {{
      font-weight: 700;
    }}
    #bottom-cta .bottom-cta-btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 14px 36px;
      background: {cor_marca};
      color: #ffffff;
      font-size: 1rem;
      font-weight: 700;
      border-radius: 50px;
      border: none;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
    }}
    #bottom-cta .bottom-cta-btn:hover {{
      transform: translateY(-2px) scale(1.03);
      box-shadow: 0 8px 28px rgba(99, 102, 241, 0.4);
    }}
    /* Dark theme */
    html[data-theme="dark"] #bottom-cta .bottom-cta-card,
    [data-theme="dark"] #bottom-cta .bottom-cta-card {{
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(99, 102, 241, 0.15) 100%);
      border-color: rgba(99, 102, 241, 0.2);
    }}
    html[data-theme="dark"] #bottom-cta .bottom-cta-text,
    [data-theme="dark"] #bottom-cta .bottom-cta-text {{
      color: #e2e8f0;
    }}
    @media (max-width: 768px) {{
      #bottom-cta {{
        padding: 16px 24px 56px 24px;
      }}
      #bottom-cta .bottom-cta-card {{
        padding: 32px 24px;
      }}
    }}
    </style>
    <section id="contato" class="cta-section">
        <div class="container">
            <span class="cta-eyebrow">Contato</span>
            <h2 class="cta-title">{_escape_html_attr(cta_titulo)}</h2>
            <p class="cta-subtitle">{_escape_html_attr(cta_subtitulo)}</p>
            <form id="lead-form" class="lead-form" autocomplete="on">
                <input type="hidden" name="keyword" value="{_escape_html_attr(keyword)}">
                <input type="hidden" name="local" value="{_escape_html_attr(local)}">
                <div class="lead-form-fields">
                    <div class="lead-form-field">
                        <label for="lead-nome">Seu nome</label>
                        <input type="text" id="lead-nome" name="nome" placeholder="Como podemos te chamar?" required autocomplete="name">
                    </div>
                    <div class="lead-form-field">
                        <label for="lead-whatsapp">Seu WhatsApp</label>
                        <input type="tel" id="lead-whatsapp" name="whatsapp" placeholder="(11) 99999-9999" required autocomplete="tel">
                    </div>
                </div>
                <button type="submit" class="btn btn-whatsapp">
                    {_WA_ICON} Iniciar Conversa pelo WhatsApp
                </button>
                <p class="lead-form-hint">Ao enviar, você será direcionado para o WhatsApp do especialista.</p>
            </form>
        </div>
    </section>
    <section id="bottom-cta">
        <div class="bottom-cta-card">
            <p class="bottom-cta-text">
                <strong>{_escape_html_attr(empresa_nome)}</strong> atende em {_escape_html_attr(local)} e região.
            </p>
            <a href="#contato" class="bottom-cta-btn" onclick="event.preventDefault();document.getElementById('contato').scrollIntoView({{behavior:'smooth',block:'center'}})">
                {_WA_ICON} Falar Agora
            </a>
        </div>
    </section>
    """
    
    # 4. Configuração e script JS
    widget_script = f"""
    <!-- Widget de Captura de Leads -->
    <script>
    window.AUTORIDADE_WIDGET = {{
      workerUrl: "{_escape_html_attr(worker_url)}",
      clientToken: "{_escape_html_attr(client_token)}",
      dominio: "{_escape_html_attr(dominio)}",
      empresaNome: "{_escape_html_attr(empresa_nome)}",
      whatsappNumero: "{_escape_html_attr(whatsapp_num)}",
      keyword: "{_escape_html_attr(keyword)}",
      local: "{_escape_html_attr(local)}"
    }};
    </script>
    <script src="js/widget.js?v=2"></script>
    
    <!-- Integrador do Formulário de Leads na Home Premium -->
    <script>
    (function() {{
      function integrateForm() {{
        var contato = document.getElementById('contato');
        if (!contato) return false;
        
        var root = document.getElementById('root');
        if (!root) return false;
        
        var sections = root.querySelectorAll('section');
        if (sections.length === 0) return false; // React ainda não renderizou

        // 1. Encontrar e ocultar a MegaCTA nativa do React (tem h2 + link wa.me)
        var megaCta = null;
        sections.forEach(function(sec) {{
          var h2 = sec.querySelector('h2');
          var hasWa = !!sec.querySelector('a[href*="wa.me"]');
          if (h2 && hasWa) {{ megaCta = sec; }}
        }});
        if (megaCta) {{ megaCta.style.display = 'none'; }}

        // 1b. Redirecionar o botão do Hero (1ª seção) para #contato via seletor semântico.
        //     O CSS já cuida de ocultar os wa.me das demais seções — sem magia de índice.
        var heroWaBtn = root.querySelector('section:first-of-type a[href*="wa.me"]');
        if (heroWaBtn) {{
          heroWaBtn.href = '#contato';
          heroWaBtn.onclick = function(e) {{
            e.preventDefault();
            var c = document.getElementById('contato');
            if (c) c.scrollIntoView({{behavior: 'smooth', block: 'start'}});
          }};
        }}

        // 2. Encontrar a seção de Autoridade/Sobre Nós
        //    Identificada pelo eyebrow "SOBRE NÓS" (span/p com esse texto)
        //    ou como fallback pela 3ª section do #root
        var authoritySection = null;
        sections.forEach(function(sec) {{
          var texts = sec.querySelectorAll('span, p, div');
          texts.forEach(function(el) {{
            if (el.children.length === 0 && el.textContent.trim().toUpperCase() === 'SOBRE NÓS') {{
              authoritySection = sec;
            }}
          }});
        }});
        // Fallback: 3ª seção do root (Hero=0, Serviços=1, Sobre=2)
        if (!authoritySection && sections.length >= 3) {{
          authoritySection = sections[2];
        }}
        if (!authoritySection) return false;

        // 3. Inserir #contato imediatamente APÓS a seção de Autoridade
        var parent = authoritySection.parentNode;
        var nextSibling = authoritySection.nextSibling;
        if (nextSibling) {{
          parent.insertBefore(contato, nextSibling);
        }} else {{
          parent.appendChild(contato);
        }}

        // 4. Tornar o form visível
        contato.style.display = 'block';

        // 5. Posicionar bottom-cta antes do footer
        var bottomCta = document.getElementById('bottom-cta');
        if (bottomCta) {{
          var footer = root.querySelector('footer');
          if (footer) {{
            footer.parentNode.insertBefore(bottomCta, footer);
          }}
          bottomCta.style.display = 'block';
        }}
        
        return true;
      }}
      
      var _attempts = 0;
      function tryIntegrate() {{
        _attempts++;
        if (!integrateForm() && _attempts < 15) {{
          setTimeout(tryIntegrate, 300); // até 15 tentativas (~4.5s)
        }}
      }}
      
      if (document.readyState === 'complete') {{
        setTimeout(tryIntegrate, 200);
      }} else {{
        window.addEventListener('load', function() {{
          setTimeout(tryIntegrate, 200);
        }});
      }}
    }})();
    </script>
    """
    
    injection = f"{form_html}\n{widget_script}"
    html = html.replace('</body>', f'{injection}\n</body>', 1)
    
    return html


def _copy_assets(dist_dir: str, output_dir: str):
    """Copia a pasta assets/ do dist para o output (JS/CSS bundled)."""
    src_assets = os.path.join(dist_dir, 'assets')
    dst_assets = os.path.join(output_dir, 'assets')
    
    if os.path.exists(src_assets):
        # Remover assets anteriores se existirem
        if os.path.exists(dst_assets):
            shutil.rmtree(dst_assets)
        shutil.copytree(src_assets, dst_assets)



def _escape_html_attr(value: str) -> str:
    """Escapa caracteres especiais para uso em atributos HTML."""
    return (
        value
        .replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
