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
        dest = os.path.join(output_dir, 'hero-image.jpg')
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

    # Injetar canonical, og:url e robots antes do </head>
    extra_tags = (
        f'\n    <link rel="canonical" href="{canonical_url}">'
        f'\n    <meta property="og:url" content="{canonical_url}">'
        f'\n    <meta name="robots" content="index, follow">'
    )
    html = html.replace('</head>', extra_tags + '\n</head>', 1)

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
      } else if (label.indexOf('cidade') > -1 && map.cidades) {
        slugObj = map.cidades;
        titlePrefix = (d.empresa && d.empresa.categoria ? d.empresa.categoria : '') + ' em {city}';
      }
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
    
    # 3. HTML Form e CSS Inline para o container (seção oculta inicialmente)
    form_html = f"""
    <style>
    /* Container styles for injected contact section */
    #contato {{
      display: none; /* Oculto até o integrador posicionar */
    }}
    #contato .container {{
      max-width: 640px;
      margin: 0 auto;
      padding: 0 24px;
      text-align: center;
    }}
    #contato .cta-title {{
      font-size: 1.75rem;
      font-weight: 700;
      margin-bottom: 8px;
      color: var(--foreground, #0f172a);
    }}
    #contato .cta-subtitle {{
      font-size: 0.95rem;
      color: var(--muted-foreground, #64748b);
      margin-bottom: 32px;
      line-height: 1.6;
    }}
    /* Dark theme */
    html[data-theme="dark"] #contato .cta-title,
    [data-theme="dark"] #contato .cta-title {{
      color: var(--foreground, #e2e8f0);
    }}
    </style>
    <section id="contato" class="cta-section">
        <div class="container">
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
                    <i class="fab fa-whatsapp"></i> Iniciar Conversa pelo WhatsApp
                </button>
                <p class="lead-form-hint">Ao enviar, você será direcionado para o WhatsApp do especialista.</p>
            </form>
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
        var form = document.getElementById('contato');
        if (!form) return false;
        
        var sections = document.querySelectorAll('#root section');
        var megaCta = null;
        
        sections.forEach(function(sec) {{
          var h2 = sec.querySelector('h2');
          if (h2 && sec.querySelector('a[href*="wa.me"]')) {{
            megaCta = sec;
          }}
        }});
        
        if (!megaCta) return false;
        
        var innerContainer = megaCta.querySelector(':scope > div');
        if (innerContainer) {{
          innerContainer.innerHTML = '';
          innerContainer.appendChild(form.querySelector('.container') || form);
        }}
        
        form.style.display = '';
        
        if (form.parentNode && form.parentNode !== innerContainer) {{
          form.parentNode.removeChild(form);
        }}
        
        return true;
      }}
      
      function tryIntegrate() {{
        if (!integrateForm()) {{
          setTimeout(tryIntegrate, 200);
        }}
      }}
      
      if (document.readyState === 'complete') {{
        setTimeout(tryIntegrate, 300);
      }} else {{
        window.addEventListener('load', function() {{
          setTimeout(tryIntegrate, 300);
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
