"""Testes para core/output_builder.py — setup de output e fallback index."""
import json
from pathlib import Path
from unittest.mock import patch
from core.output_builder import setup_output_dir, generate_fallback_index


def _make_config():
    return {
        'empresa': {
            'nome': 'TestEmpresa',
            'dominio': 'test.com.br',
            'categoria': 'Teste',
            'telefone_whatsapp': '5511999990000',
            'telefone_ligar': '5511999990000',
            'cor_marca': '#FF0000',
            'horario': 'Seg-Sex 8h-18h',
            'google_maps_embed': 'https://maps.google.com/embed',
        },
    }


class TestSetupOutputDir:
    def test_creates_output_directory(self, tmp_path):
        out = tmp_path / "site_output"
        setup_output_dir(str(out), _make_config())
        assert out.exists()

    def test_creates_dados_js(self, tmp_path):
        out = tmp_path / "out"
        setup_output_dir(str(out), _make_config())
        dados_path = out / "js" / "dados.js"
        assert dados_path.exists()
        content = dados_path.read_text(encoding='utf-8')
        assert 'TestEmpresa' in content
        assert 'DadosSite' in content

    def test_dados_js_contains_config_fields(self, tmp_path):
        out = tmp_path / "out"
        setup_output_dir(str(out), _make_config())
        content = (out / "js" / "dados.js").read_text(encoding='utf-8')
        # Extract the JSON part
        json_str = content.split('= ', 1)[1].rstrip(';\n')
        data = json.loads(json_str)
        assert data['empresa_nome'] == 'TestEmpresa'
        assert data['empresa_categoria'] == 'Teste'
        assert data['dominio'] == 'test.com.br'
        assert '5511999990000' in data['telefone_whatsapp']
        assert data['whatsapp_link'].startswith('https://wa.me/')

    def test_copies_template_assets(self, tmp_path):
        # Create fake template dirs
        templates = tmp_path / "templates"
        (templates / "css").mkdir(parents=True)
        (templates / "css" / "style.css").write_text("body { color: {{cor_marca}}; }", encoding='utf-8')
        (templates / "js").mkdir()
        (templates / "js" / "main.js").write_text("// js", encoding='utf-8')

        out = tmp_path / "out"
        with patch('core.output_builder.TEMPLATES_DIR', templates):
            setup_output_dir(str(out), _make_config())

        assert (out / "css" / "style.css").exists()
        assert (out / "js" / "main.js").exists()

    def test_processes_css_variables(self, tmp_path):
        templates = tmp_path / "templates"
        (templates / "css").mkdir(parents=True)
        (templates / "css" / "style.css").write_text(
            "body { color: {{cor_marca}}; }", encoding='utf-8'
        )

        out = tmp_path / "out"
        with patch('core.output_builder.TEMPLATES_DIR', templates):
            setup_output_dir(str(out), _make_config())

        css = (out / "css" / "style.css").read_text(encoding='utf-8')
        assert '#FF0000' in css
        assert '{{cor_marca}}' not in css


class TestGenerateFallbackIndex:
    def test_generates_index_from_template(self, tmp_path):
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "index.html").write_text(
            "<html><title>{{empresa_nome}}</title></html>", encoding='utf-8'
        )

        out = tmp_path / "out"
        out.mkdir()
        with patch('core.output_builder.TEMPLATES_DIR', templates):
            generate_fallback_index(_make_config(), str(out))

        index = out / "index.html"
        assert index.exists()
        content = index.read_text(encoding='utf-8')
        assert 'TestEmpresa' in content

    def test_no_template_no_crash(self, tmp_path):
        templates = tmp_path / "empty_templates"
        templates.mkdir()
        out = tmp_path / "out"
        out.mkdir()
        with patch('core.output_builder.TEMPLATES_DIR', templates):
            # Should not raise
            generate_fallback_index(_make_config(), str(out))
        assert not (out / "index.html").exists()
