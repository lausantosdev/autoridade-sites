"""Testes para core/validator.validate_page_html e _validate_page"""
from core.validator import validate_page_html, _validate_page


def _make_valid_html(word_count=200):
    """Helper: gera HTML válido mínimo com N palavras."""
    words = " ".join(["palavra"] * word_count)
    return f"""<!DOCTYPE html>
<html><head><title>Piso Vinílico em SP</title>
<meta name="description" content="Descrição do serviço"></head>
<body>
<h1>Piso Vinílico em São Paulo</h1>
<h2>Seção 1</h2><p>{words}</p>
<h2>Seção 2</h2><p>Conteúdo</p>
<h2>Seção 3</h2><p>Conteúdo</p>
<h2>Seção 4</h2><p>Conteúdo</p>
<h2>Seção 5</h2><p>Conteúdo</p>
<h2>Seção 6</h2><p>Conteúdo</p>
<a href="outro.html">Link</a>
<a href="mais.html">Link 2</a>
</body></html>"""


class TestValidatePageHtml:
    """Testes para validate_page_html (validação inline durante geração)."""

    def test_missing_title_is_error(self):
        html = "<html><head></head><body><p>conteúdo</p></body></html>"
        result = validate_page_html("test.html", html)
        assert not result['valid']
        assert any("Título" in e or "title" in e.lower() for e in result['errors'])

    def test_placeholder_in_body_is_error(self):
        html = _make_valid_html(600)
        html = html.replace("Seção 1", "@seo_h2_1")
        result = validate_page_html("test.html", html)
        assert not result['valid']
        assert any("placeholder" in e.lower() for e in result['errors'])

    def test_css_at_rule_not_flagged(self):
        """@media e @keyframes não devem ser tratados como placeholders."""
        html = _make_valid_html(600)
        html = html.replace("</head>", "<style>@media (max-width:768px){} @keyframes fade{}</style></head>")
        result = validate_page_html("test.html", html)
        # Não deve ter erro de placeholder por causa de @media/@keyframes
        placeholder_errors = [e for e in result['errors'] if 'placeholder' in e.lower()]
        assert len(placeholder_errors) == 0

    def test_config_var_not_replaced_is_error(self):
        html = _make_valid_html(600).replace("Piso Vinílico em SP", "{{empresa_nome}}")
        result = validate_page_html("test.html", html)
        assert not result['valid']
        assert any("Config var" in e or "config" in e.lower() for e in result['errors'])

    def test_under_500_words_is_blocking_error(self):
        html = _make_valid_html(100)
        result = validate_page_html("test.html", html)
        assert not result['valid']
        assert any("500" in e for e in result['errors'])

    def test_500_to_899_words_is_warning_not_error(self):
        html = _make_valid_html(600)
        result = validate_page_html("test.html", html)
        assert result['valid']
        assert any("900" in w or "ideal" in w.lower() for w in result['warnings'])

    def test_few_h2s_is_warning(self):
        html = """<!DOCTYPE html><html><head><title>Teste</title></head>
        <body><h1>Titulo</h1><h2>Só um</h2>
        <p>{}</p></body></html>""".format(" ".join(["texto"] * 600))
        result = validate_page_html("test.html", html)
        assert any("H2" in w for w in result['warnings'])

    def test_valid_page_has_no_errors(self):
        html = _make_valid_html(1000)
        result = validate_page_html("test.html", html)
        assert result['valid']
        assert result['errors'] == []
        assert result['word_count'] > 900


class TestValidatePage:
    """Testes para _validate_page (validação pós-geração de site completo)."""

    def test_missing_title_is_error(self):
        html = "<html><head></head><body>conteúdo</body></html>"
        result = _validate_page("test.html", html)
        assert len(result['errors']) > 0

    def test_placeholder_at_in_title_is_error(self):
        html = "<html><head><title>@titulo</title></head><body>x</body></html>"
        result = _validate_page("test.html", html)
        assert any("Placeholder" in e or "placeholder" in e.lower() for e in result['errors'])

    def test_valid_page_zero_errors(self):
        html = _make_valid_html(1000)
        result = _validate_page("test.html", html)
        assert result['errors'] == []
