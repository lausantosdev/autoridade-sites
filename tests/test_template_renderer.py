"""Testes para core/template_renderer.replace_config_vars"""
from datetime import datetime
from core.template_renderer import replace_config_vars


def _make_config(**overrides):
    """Helper: cria config mínimo para testes."""
    config = {
        'empresa': {
            'nome': 'Clean Pro',
            'dominio': 'cleanpro.com.br',
            'categoria': 'Limpeza de Estofados',
            'telefone_whatsapp': '5541999998888',
            'telefone_ligar': '5541999998888',
            'cor_marca': '#2563EB',
            'horario': 'Segunda a Sexta, 8h às 18h',
            'google_maps_embed': '',
            'endereco': '',
        },
        'seo': {
            'palavras_chave': ['Limpeza de Sofá', 'Higienização de Estofados'],
            'locais': ['Curitiba', 'São José dos Pinhais'],
        },
        'leads': {
            'worker_url': '',
            'client_token': '',
        },
    }
    # Aplicar overrides
    for key, value in overrides.items():
        parts = key.split('.')
        d = config
        for p in parts[:-1]:
            d = d[p]
        d[parts[-1]] = value
    return config


class TestReplaceConfigVars:

    def test_empresa_nome(self):
        config = _make_config()
        result = replace_config_vars("Olá {{empresa_nome}}!", config)
        assert result == "Olá Clean Pro!"

    def test_cidade_principal_first_local(self):
        config = _make_config()
        result = replace_config_vars("Em {{cidade_principal}}", config)
        assert result == "Em Curitiba"

    def test_cidade_principal_empty_without_locais(self):
        config = _make_config()
        config['seo']['locais'] = []
        result = replace_config_vars("Em {{cidade_principal}}", config)
        assert result == "Em "

    def test_cor_marca_rgb(self):
        config = _make_config()
        result = replace_config_vars("rgb({{cor_marca_rgb}})", config)
        assert result == "rgb(37, 99, 235)"

    def test_minimal_config_returns_string(self):
        config = _make_config()
        result = replace_config_vars("{{empresa_nome}} {{dominio}}", config)
        assert isinstance(result, str)
        assert "Clean Pro" in result

    def test_locais_footer_multiple(self):
        config = _make_config()
        result = replace_config_vars("{{locais_footer}}", config)
        assert "Curitiba" in result
        assert "São José dos Pinhais" in result
        assert "fa-map-marker-alt" in result   # ícone presente
        assert "<a href=" not in result         # sem hyperlinks — removido intencionalmente

    def test_ano_current_year(self):
        config = _make_config()
        result = replace_config_vars("{{ano}}", config)
        assert result == str(datetime.now().year)

    def test_endereco_footer_empty_when_absent(self):
        config = _make_config()
        config['empresa']['endereco'] = ''
        result = replace_config_vars("{{endereco_footer}}", config)
        assert result.strip() == ""

    def test_endereco_footer_with_icon_when_present(self):
        config = _make_config()
        config['empresa']['endereco'] = 'Rua XV, 100'
        result = replace_config_vars("{{endereco_footer}}", config)
        assert "fa-location-dot" in result
        assert "Rua XV, 100" in result

    def test_theme_mode_default_dark(self):
        config = _make_config()
        result = replace_config_vars("{{theme_mode}}", config)
        assert result == "dark"

    def test_worker_url_empty_without_leads(self):
        config = _make_config()
        del config['leads']
        result = replace_config_vars("{{worker_url}}", config)
        assert result == ""

    def test_unknown_placeholder_stays(self):
        config = _make_config()
        result = replace_config_vars("{{inexistente}}", config)
        assert result == "{{inexistente}}"
