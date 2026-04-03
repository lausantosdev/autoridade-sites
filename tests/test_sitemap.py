"""Testes para core/sitemap_generator.py — geração de sitemap.xml e mapa-do-site.html."""
import os
from core.sitemap_generator import generate_sitemap, _generate_sitemap_xml, _generate_sitemap_html


def _make_config():
    return {
        'empresa': {
            'nome': 'Clean Pro',
            'dominio': 'cleanpro.com.br',
            'cor_marca': '#2563EB',
        }
    }


def _make_pages():
    return [
        {'title': 'Limpeza de Sofá em Curitiba', 'filename': 'limpeza-de-sofa-curitiba.html'},
        {'title': 'Higienização em SJP', 'filename': 'higienizacao-sjp.html'},
        {'title': 'Impermeabilização em Araucária', 'filename': 'impermeabilizacao-araucaria.html'},
    ]


class TestGenerateSitemapXml:
    def test_creates_sitemap_file(self, tmp_path):
        _generate_sitemap_xml(_make_pages(), 'https://cleanpro.com.br', str(tmp_path))
        assert (tmp_path / 'sitemap.xml').exists()

    def test_contains_all_urls(self, tmp_path):
        pages = _make_pages()
        _generate_sitemap_xml(pages, 'https://cleanpro.com.br', str(tmp_path))
        content = (tmp_path / 'sitemap.xml').read_text(encoding='utf-8')
        # index + mapa-do-site + 3 pages = 5 URLs
        assert content.count('<loc>') == 5
        assert 'limpeza-de-sofa-curitiba.html' in content
        assert 'higienizacao-sjp.html' in content
        assert 'impermeabilizacao-araucaria.html' in content

    def test_xml_header(self, tmp_path):
        _generate_sitemap_xml([], 'https://x.com', str(tmp_path))
        content = (tmp_path / 'sitemap.xml').read_text(encoding='utf-8')
        assert '<?xml version="1.0"' in content
        assert 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in content

    def test_homepage_has_priority_1(self, tmp_path):
        _generate_sitemap_xml([], 'https://x.com', str(tmp_path))
        content = (tmp_path / 'sitemap.xml').read_text(encoding='utf-8')
        # Homepage deve ter priority 1.0
        idx = content.index('index.html')
        block = content[idx:idx+200]
        assert '<priority>1.0</priority>' in block


class TestGenerateSitemapHtml:
    def test_creates_html_file(self, tmp_path):
        _generate_sitemap_html(_make_pages(), 'https://cleanpro.com.br', _make_config(), str(tmp_path))
        assert (tmp_path / 'mapa-do-site.html').exists()

    def test_contains_links_to_all_pages(self, tmp_path):
        pages = _make_pages()
        _generate_sitemap_html(pages, 'https://cleanpro.com.br', _make_config(), str(tmp_path))
        content = (tmp_path / 'mapa-do-site.html').read_text(encoding='utf-8')
        for page in pages:
            assert page['filename'] in content
            assert page['title'] in content

    def test_includes_empresa_name(self, tmp_path):
        _generate_sitemap_html([], 'https://x.com', _make_config(), str(tmp_path))
        content = (tmp_path / 'mapa-do-site.html').read_text(encoding='utf-8')
        assert 'Clean Pro' in content

    def test_includes_cor_marca(self, tmp_path):
        _generate_sitemap_html([], 'https://x.com', _make_config(), str(tmp_path))
        content = (tmp_path / 'mapa-do-site.html').read_text(encoding='utf-8')
        assert '#2563EB' in content


class TestGenerateSitemap:
    def test_creates_both_files(self, tmp_path):
        generate_sitemap(_make_pages(), _make_config(), str(tmp_path))
        assert (tmp_path / 'sitemap.xml').exists()
        assert (tmp_path / 'mapa-do-site.html').exists()

    def test_empty_pages(self, tmp_path):
        generate_sitemap([], _make_config(), str(tmp_path))
        xml = (tmp_path / 'sitemap.xml').read_text(encoding='utf-8')
        # Only index + mapa-do-site
        assert xml.count('<loc>') == 2
