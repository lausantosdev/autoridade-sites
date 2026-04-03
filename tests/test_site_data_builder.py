"""Testes para core/site_data_builder — funções puras sem chamada de API."""
import json
from core.site_data_builder import (
    _build_services,
    _build_faqs,
    _build_faq_schema,
    _build_local_business_schema,
    _fallback_content,
)


def _make_ai_content():
    """AI content mockado com todos os campos esperados."""
    return {
        'service_1_description': 'Limpeza profissional de sofás',
        'service_1_icon': 'Zap',
        'service_2_description': 'Higienização completa de estofados',
        'service_2_icon': 'Shield',
        'service_3_description': 'Impermeabilização de tecidos',
        'service_3_icon': 'Star',
        'faq_1_question': 'Quanto tempo demora?',
        'faq_1_answer': 'Em média 2 a 4 horas dependendo do tamanho do sofá.',
        'faq_2_question': 'Danifica o tecido?',
        'faq_2_answer': 'Não, usamos produtos específicos para cada tipo de tecido.',
        'faq_3_question': 'Atendem toda a cidade?',
        'faq_3_answer': 'Sim, atendemos Curitiba e região metropolitana.',
    }


def _make_empresa():
    """Empresa mockada."""
    return {
        'nome': 'Clean Pro',
        'dominio': 'cleanpro.com.br',
        'categoria': 'Limpeza de Estofados',
        'telefone_whatsapp': '5541999998888',
        'horario': 'Seg-Sex 8h-18h',
        'endereco': '',
    }


class TestBuildServices:
    def test_returns_correct_count(self):
        palavras = ['Limpeza de Sofá', 'Higienização', 'Impermeabilização']
        result = _build_services(palavras, _make_ai_content())
        assert len(result) == 3

    def test_uses_ai_descriptions(self):
        palavras = ['Limpeza de Sofá']
        result = _build_services(palavras, _make_ai_content())
        assert result[0]['description'] == 'Limpeza profissional de sofás'

    def test_fallback_on_empty_ai(self):
        palavras = ['Limpeza de Sofá']
        result = _build_services(palavras, {})
        assert 'profissional' in result[0]['description'].lower()

    def test_invalid_icon_gets_fallback(self):
        ai = {'service_1_icon': 'NaoExiste', 'service_1_description': 'Desc'}
        palavras = ['Limpeza de Sofá']
        result = _build_services(palavras, ai)
        assert result[0]['iconName'] == 'Zap'

    def test_empty_palavras_returns_fallback(self):
        result = _build_services([], {})
        assert len(result) == 1
        assert result[0]['title'] == 'Serviço Profissional'


class TestBuildFaqs:
    def test_extracts_three_faqs(self):
        result = _build_faqs(_make_ai_content())
        assert len(result) == 3

    def test_each_faq_has_question_and_answer(self):
        result = _build_faqs(_make_ai_content())
        for faq in result:
            assert 'question' in faq
            assert 'answer' in faq
            assert len(faq['question']) > 0
            assert len(faq['answer']) > 0

    def test_empty_ai_returns_empty_list(self):
        result = _build_faqs({})
        assert result == []


class TestBuildFaqSchema:
    def test_generates_valid_jsonld(self):
        result = _build_faq_schema(_make_ai_content())
        assert result != ''
        parsed = json.loads(result)
        assert parsed['@context'] == 'https://schema.org'
        assert parsed['@type'] == 'FAQPage'
        assert len(parsed['mainEntity']) == 3

    def test_empty_without_faqs(self):
        result = _build_faq_schema({})
        assert result == ''


class TestBuildLocalBusinessSchema:
    def test_generates_valid_jsonld(self):
        empresa = _make_empresa()
        result = _build_local_business_schema(
            empresa, '(41) 99999-8888', ['Curitiba', 'SJP'],
            description='Limpeza profissional'
        )
        parsed = json.loads(result)
        assert parsed['@context'] == 'https://schema.org'
        assert parsed['@type'] == 'LocalBusiness'
        assert parsed['name'] == 'Clean Pro'
        assert parsed['telephone'] == '(41) 99999-8888'
        assert parsed['address']['addressLocality'] == 'Curitiba'

    def test_area_served_multiple_cities(self):
        empresa = _make_empresa()
        result = _build_local_business_schema(
            empresa, '(41) 99999-8888', ['Curitiba', 'SJP', 'Araucária', 'Colombo']
        )
        parsed = json.loads(result)
        assert isinstance(parsed['areaServed'], list)
        assert len(parsed['areaServed']) == 4

    def test_street_address_when_present(self):
        empresa = _make_empresa()
        empresa['endereco'] = 'Rua XV, 100'
        result = _build_local_business_schema(
            empresa, '(41) 99999-8888', ['Curitiba']
        )
        parsed = json.loads(result)
        assert parsed['address']['streetAddress'] == 'Rua XV, 100'


class TestFallbackContent:
    def test_returns_all_expected_keys(self):
        empresa = _make_empresa()
        palavras = ['Limpeza de Sofá', 'Higienização']
        result = _fallback_content(empresa, palavras)
        expected_keys = [
            'hero_badge_text', 'hero_title_line_1', 'hero_title_line_2',
            'hero_subtitle', 'services_title', 'services_subtitle',
            'authority_title', 'authority_manifesto',
            'mega_cta_title', 'mega_cta_subtitle', 'footer_descricao',
        ]
        for key in expected_keys:
            assert key in result, f"Chave ausente: {key}"

    def test_generates_service_fallbacks(self):
        empresa = _make_empresa()
        palavras = ['Limpeza de Sofá', 'Higienização']
        result = _fallback_content(empresa, palavras)
        assert 'service_1_description' in result
        assert 'service_1_icon' in result
        assert 'service_2_description' in result
