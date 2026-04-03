"""Testes para validate_site() e generate_report() em core/validator.py."""
import os
from core.validator import validate_site, generate_report, _validate_page


def _make_config():
    return {
        'empresa': {
            'nome': 'Clean Pro',
            'dominio': 'cleanpro.com.br',
            'categoria': 'Limpeza',
            'telefone_whatsapp': '5541999998888',
            'cor_marca': '#2563EB',
        },
        'api': {'max_retries': 3},
    }


def _make_valid_html(title="Limpeza em Curitiba", word_count=1000):
    """Gera HTML válido com N palavras."""
    words = " ".join(["palavra"] * word_count)
    return f"""<!DOCTYPE html>
<html><head>
<title>{title}</title>
<meta name="description" content="Descrição do serviço profissional">
</head><body>
<h1>{title}</h1>
<h2>Seção 1</h2><p>{words}</p>
<h2>Seção 2</h2><p>Conteúdo.</p>
<h2>Seção 3</h2><p>Conteúdo.</p>
<h2>Seção 4</h2><p>Conteúdo.</p>
<h2>Seção 5</h2><p>Conteúdo.</p>
<h2>Seção 6</h2><p>Conteúdo.</p>
<a href="outro.html">Link 1</a>
<a href="mais.html">Link 2</a>
</body></html>"""


class TestValidateSite:
    def test_valid_site_returns_all_valid(self, tmp_path):
        for i in range(3):
            (tmp_path / f"pagina-{i}.html").write_text(
                _make_valid_html(f"Página {i}"), encoding='utf-8'
            )
        results = validate_site(str(tmp_path), _make_config())
        assert results['total_pages'] == 3
        assert results['valid_pages'] == 3
        assert len(results['errors']) == 0

    def test_counts_total_words(self, tmp_path):
        (tmp_path / "p1.html").write_text(
            _make_valid_html(word_count=500), encoding='utf-8'
        )
        results = validate_site(str(tmp_path), _make_config())
        assert results['stats']['total_words'] > 0

    def test_detects_errors(self, tmp_path):
        # HTML with placeholder in title
        (tmp_path / "broken.html").write_text(
            "<html><head><title>@titulo</title></head><body><p>short</p></body></html>",
            encoding='utf-8'
        )
        results = validate_site(str(tmp_path), _make_config())
        assert len(results['errors']) > 0

    def test_empty_directory(self, tmp_path):
        results = validate_site(str(tmp_path), _make_config())
        assert results['total_pages'] == 0
        assert results['valid_pages'] == 0

    def test_stats_has_required_keys(self, tmp_path):
        (tmp_path / "p.html").write_text(_make_valid_html(), encoding='utf-8')
        results = validate_site(str(tmp_path), _make_config())
        assert 'total_words' in results['stats']
        assert 'avg_words_per_page' in results['stats']
        assert 'total_size_kb' in results['stats']


class TestValidatePage:
    def test_placeholder_in_meta_description(self):
        html = '<html><head><title>Ok</title><meta name="description" content="@meta_desc"></head><body>' + " ".join(["w"]*600) + '</body></html>'
        result = _validate_page("test.html", html)
        assert any('Placeholder' in e for e in result['errors'])

    def test_missing_h1_is_warning(self):
        html = '<html><head><title>Ok</title><meta name="description" content="desc"></head><body>' + " ".join(["w"]*1000) + '</body></html>'
        result = _validate_page("test.html", html)
        assert any('H1' in w for w in result['warnings'])

    def test_config_vars_detected(self):
        html = '<html><head><title>Ok</title></head><body>{{cor_marca}} ' + " ".join(["w"]*600) + '</body></html>'
        result = _validate_page("test.html", html)
        assert any('Config vars' in e for e in result['errors'])

    def test_low_word_count_warning(self):
        html = '<html><head><title>Ok</title><meta name="description" content="desc"></head><body><h1>T</h1>' + " ".join(["w"]*500) + '</body></html>'
        result = _validate_page("test.html", html)
        assert any('palavras' in w for w in result['warnings'])

    def test_few_internal_links_warning(self):
        html = '<html><head><title>Ok</title><meta name="description" content="desc"></head><body><h1>T</h1>' + " ".join(["w"]*1000) + '</body></html>'
        result = _validate_page("test.html", html)
        assert any('links internos' in w for w in result['warnings'])


class TestGenerateReport:
    def test_report_contains_empresa(self, tmp_path):
        results = {
            'total_pages': 5,
            'valid_pages': 4,
            'errors': ['page1.html: Erro X'],
            'warnings': ['page2.html: Warning Y'],
            'stats': {'total_words': 5000, 'avg_words_per_page': 1000, 'total_size_kb': 200},
        }
        api_stats = {
            'calls': 10, 'input_tokens': 5000, 'output_tokens': 3000,
            'cost_usd': 0.05, 'cost_brl': 0.29,
        }
        report = generate_report(results, _make_config(), api_stats, str(tmp_path))
        assert 'Clean Pro' in report
        assert 'Erro X' in report
        assert 'Warning Y' in report

    def test_report_saves_file(self, tmp_path):
        results = {
            'total_pages': 1, 'valid_pages': 1,
            'errors': [], 'warnings': [],
            'stats': {'total_words': 1000, 'avg_words_per_page': 1000, 'total_size_kb': 10},
        }
        api_stats = {
            'calls': 1, 'input_tokens': 100, 'output_tokens': 50,
            'cost_usd': 0.001, 'cost_brl': 0.006,
        }
        generate_report(results, _make_config(), api_stats, str(tmp_path))
        reports_dir = os.path.join(str(tmp_path), '..', 'reports')
        report_files = os.listdir(reports_dir)
        assert len(report_files) == 1
        assert report_files[0].endswith('_report.md')

    def test_report_with_retries(self, tmp_path):
        results = {
            'total_pages': 2, 'valid_pages': 2,
            'errors': [], 'warnings': [],
            'stats': {'total_words': 2000, 'avg_words_per_page': 1000, 'total_size_kb': 20},
        }
        api_stats = {
            'calls': 4, 'input_tokens': 200, 'output_tokens': 100,
            'cost_usd': 0.002, 'cost_brl': 0.012,
        }
        retry_log = [
            {'page': 'limpeza.html', 'attempt': 1, 'errors': ['Placeholder @titulo']},
            {'page': 'limpeza.html', 'attempt': 2, 'errors': ['Placeholder @titulo']},
            {'page': 'piso.html', 'attempt': 1, 'errors': ['Pouco conteúdo']},
        ]
        report = generate_report(results, _make_config(), api_stats, str(tmp_path), retry_log=retry_log)
        assert 'Retries' in report
        assert 'limpeza.html' in report
        assert 'piso.html' in report
        assert 'Recuperadas' in report
