"""Testes de integração: pipeline completo config → API mockada → HTML → validação."""
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
from core.page_generator import _generate_single_page
from core.validator import _validate_page


def _make_full_config():
    """Config completo para testes de integração."""
    return {
        'empresa': {
            'nome': 'Clean Pro Estofados',
            'dominio': 'cleanproestofados.com.br',
            'categoria': 'Limpeza de Estofados',
            'telefone_whatsapp': '5541999998888',
            'telefone_ligar': '5541999998888',
            'cor_marca': '#2563EB',
            'horario': 'Segunda a Sexta, 8h às 18h',
            'google_maps_embed': '',
            'endereco': 'Rua XV, 100 - Curitiba',
        },
        'seo': {
            'palavras_chave': ['Limpeza de Sofá', 'Higienização de Estofados'],
            'locais': ['Curitiba', 'São José dos Pinhais'],
        },
        'api': {
            'provider': 'openrouter',
            'model': 'deepseek/deepseek-chat',
            'max_workers': 2,
            'max_retries': 3,
        },
        'leads': {'worker_url': '', 'client_token': ''},
    }


def _make_mock_ai_response():
    """Resposta IA mockada com todos os campos esperados."""
    seo_paragraph = "A limpeza profissional de estofados é essencial para manter a saúde e a beleza de seus móveis. " * 10
    return {
        "titulo": "Limpeza de Sofá Profissional em Curitiba - Clean Pro Estofados",
        "meta_description": "Serviço profissional de limpeza de sofá em Curitiba com resultados garantidos. Clean Pro Estofados.",
        "meta_keywords": "limpeza de sofá, higienização, estofados, Curitiba",
        "hero_titulo_linha_1": "Precisa de",
        "hero_titulo_destaque": "Limpeza de Sofá",
        "hero_titulo_linha_3": "em Curitiba",
        "hero_subtitulo": "Clean Pro Estofados — profissionais qualificados para seu projeto em Curitiba",
        "diferencial_1_titulo": "Atendimento Personalizado",
        "diferencial_1_descricao": "Equipe dedicada ao seu projeto",
        "diferencial_1_icone": "fas fa-headset",
        "diferencial_2_titulo": "Equipe Qualificada",
        "diferencial_2_descricao": "Profissionais treinados e experientes",
        "diferencial_2_icone": "fas fa-medal",
        "diferencial_3_titulo": "Compromisso com Resultado",
        "diferencial_3_descricao": "Garantia de satisfação total",
        "diferencial_3_icone": "fas fa-check-circle",
        "autoridade_titulo": "Especialistas em Limpeza de Estofados em Curitiba",
        "autoridade_manifesto": "Nossa equipe é especializada em limpeza e higienização de estofados. Trabalhamos com dedicação e compromisso.",
        "cta_titulo": "Agende sua Limpeza Agora",
        "cta_subtitulo": "Fale conosco pelo WhatsApp sem compromisso",
        "faq_h2": "Perguntas Frequentes Sobre Limpeza de Sofá",
        "faq_1_pergunta": "Quanto tempo demora a limpeza de um sofá?",
        "faq_1_resposta": "O tempo varia conforme o tamanho e o estado do sofá. Em média, o processo leva de 2 a 4 horas para conclusão completa com secagem.",
        "faq_2_pergunta": "A limpeza profissional danifica o tecido?",
        "faq_2_resposta": "Não. Utilizamos produtos específicos para cada tipo de tecido, garantindo a preservação das fibras e cores originais do estofado.",
        "faq_3_pergunta": "Vocês atendem em toda Curitiba?",
        "faq_3_resposta": "Sim. Atendemos Curitiba e região metropolitana, incluindo São José dos Pinhais, com agendamento flexível.",
        "seo_h2_1": "O que é limpeza profissional de sofá e por que é importante",
        "seo_p1": seo_paragraph,
        "seo_h2_2": "Como funciona o processo de higienização de estofados",
        "seo_p2": seo_paragraph,
        "seo_h2_3": "Quando contratar limpeza profissional de sofá",
        "seo_p3": seo_paragraph,
        "seo_h2_4": "Limpeza profissional vs limpeza caseira de estofados",
        "seo_p4": seo_paragraph,
        "seo_h2_5": "Clean Pro em Curitiba: referência em limpeza de estofados",
        "seo_p5": seo_paragraph,
        "seo_h2_6": "Como solicitar limpeza de sofá em Curitiba",
        "seo_p6": seo_paragraph,
    }


def _mock_topics():
    """Tópicos mockados."""
    return {
        'palavras': ['higienização', 'impermeabilização', 'limpeza a seco'],
        'frases': ['Como cuidar do seu sofá', 'Manutenção preventiva de estofados'],
    }


def _load_test_template():
    """Carrega o template real de subpáginas."""
    template_path = Path("templates") / "page.html"
    if not template_path.exists():
        # Se não existir, criar um template mínimo para o teste
        return """<!DOCTYPE html>
<html><head>
<title>@titulo</title>
<meta name="description" content="@meta_description">
<meta name="keywords" content="@meta_keywords">
{{schema_markup}}
<link rel="canonical" href="{{canonical_url}}">
</head><body>
<h1>@hero_titulo_linha_1 @hero_titulo_destaque @hero_titulo_linha_3</h1>
<p>@hero_subtitulo</p>
<h2>@seo_h2_1</h2><p>@seo_p1</p>
<h2>@seo_h2_2</h2><p>@seo_p2</p>
<h2>@seo_h2_3</h2><p>@seo_p3</p>
<h2>@seo_h2_4</h2><p>@seo_p4</p>
<h2>@seo_h2_5</h2><p>@seo_p5</p>
<h2>@seo_h2_6</h2><p>@seo_p6</p>
<h2>@faq_h2</h2>
<p>@faq_1_pergunta</p><p>@faq_1_resposta</p>
<p>@faq_2_pergunta</p><p>@faq_2_resposta</p>
<p>@faq_3_pergunta</p><p>@faq_3_resposta</p>
<a href="outro.html">Link</a>
</body></html>"""
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    # Pré-processar com replace_config_vars (como faz generate_all_pages)
    from core.template_renderer import replace_config_vars
    return replace_config_vars(template, _make_full_config())


class TestIntegration:

    def test_generate_single_page_produces_valid_html(self, tmp_path):
        """Pipeline completo: config → API mockada → HTML gerado → validação sem erros."""
        config = _make_full_config()
        template = _load_test_template()

        mock_client = MagicMock()
        mock_client.generate_json.return_value = _make_mock_ai_response()

        page = {
            "title": "Limpeza de Sofá em Curitiba",
            "keyword": "Limpeza de Sofá",
            "location": "Curitiba",
            "filename": "limpeza-de-sofa-curitiba.html",
            "slug": "limpeza-de-sofa-curitiba",
        }
        all_pages = [
            page,
            {"title": "Higienização de Estofados em Curitiba", "keyword": "Higienização de Estofados",
             "location": "Curitiba", "filename": "higienizacao-de-estofados-curitiba.html",
             "slug": "higienizacao-de-estofados-curitiba"},
        ]

        _generate_single_page(
            page, all_pages, config, _mock_topics(),
            mock_client, template, str(tmp_path)
        )

        # Verificar que o arquivo foi criado
        output_file = tmp_path / page['filename']
        assert output_file.exists(), "HTML não foi gerado"

        # Validar estrutura do HTML gerado
        html = output_file.read_text(encoding='utf-8')
        result = _validate_page(page['filename'], html)
        assert result['errors'] == [], f"Erros de validação: {result['errors']}"

    def test_generate_page_calls_api_once_on_success(self, tmp_path):
        """Verifica que a API é chamada exatamente 1 vez se o resultado é válido."""
        config = _make_full_config()
        template = _load_test_template()

        mock_client = MagicMock()
        mock_client.generate_json.return_value = _make_mock_ai_response()

        page = {
            "title": "Limpeza de Sofá em Curitiba",
            "keyword": "Limpeza de Sofá",
            "location": "Curitiba",
            "filename": "limpeza-de-sofa-curitiba.html",
            "slug": "limpeza-de-sofa-curitiba",
        }

        _generate_single_page(
            page, [page], config, _mock_topics(),
            mock_client, template, str(tmp_path)
        )

        assert mock_client.generate_json.call_count == 1

    def test_generate_page_retries_on_empty_response(self, tmp_path):
        """Verifica que retries acontecem quando a API retorna None."""
        config = _make_full_config()
        template = _load_test_template()

        mock_client = MagicMock()
        # Primeira chamada retorna None (falha), segunda retorna dados válidos
        mock_client.generate_json.side_effect = [None, _make_mock_ai_response()]

        page = {
            "title": "Limpeza de Sofá em Curitiba",
            "keyword": "Limpeza de Sofá",
            "location": "Curitiba",
            "filename": "limpeza-de-sofa-curitiba.html",
            "slug": "limpeza-de-sofa-curitiba",
        }

        _generate_single_page(
            page, [page], config, _mock_topics(),
            mock_client, template, str(tmp_path)
        )

        assert mock_client.generate_json.call_count == 2
        assert (tmp_path / page['filename']).exists()
