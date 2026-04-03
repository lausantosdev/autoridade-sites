"""
Testes do server.py — _build_config() e endpoint upload-csv.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app, _build_config


class TestBuildConfig:
    """Testes para a função _build_config()."""

    def test_basic_fields(self):
        data = {
            'empresa_nome': 'PetVida',
            'dominio': 'petvida.com.br',
            'categoria': 'Pet Shop',
            'telefone': '5541999998888',
            'horario': 'Seg a Sex, 8h às 18h',
            'endereco': 'Rua das Flores, 123',
            'servicos': 'Banho e Tosa\nConsulta Veterinária',
            'cor_marca': '#22c55e',
            'google_maps': '',
            'keywords_manual': 'Pet Shop\nBanho e Tosa',
            'locations': 'Curitiba\nSão José dos Pinhais',
        }
        config = _build_config(data)

        assert config['empresa']['nome'] == 'PetVida'
        assert config['empresa']['dominio'] == 'petvida.com.br'
        assert config['empresa']['categoria'] == 'Pet Shop'
        assert config['empresa']['telefone_whatsapp'] == '5541999998888'
        assert config['empresa']['cor_marca'] == '#22c55e'
        assert len(config['empresa']['servicos_manuais']) == 2
        assert config['seo']['palavras_chave'] == ['Pet Shop', 'Banho e Tosa']
        assert config['seo']['locais'] == ['Curitiba', 'São José dos Pinhais']

    def test_default_values(self):
        data = {}
        config = _build_config(data)

        assert config['empresa']['nome'] == ''
        assert config['empresa']['cor_marca'] == '#2563EB'
        assert config['api']['model'] == 'deepseek/deepseek-v3.2'
        assert config['api']['max_workers'] == 30
        assert config['api']['max_retries'] == 3

    def test_google_maps_iframe_extraction(self):
        data = {
            'google_maps': '<iframe src="https://maps.google.com/embed?pb=abc123" width="600"></iframe>',
        }
        config = _build_config(data)
        assert config['empresa']['google_maps_embed'] == 'https://maps.google.com/embed?pb=abc123'

    def test_google_maps_plain_url(self):
        data = {
            'google_maps': 'https://maps.google.com/embed?pb=abc123',
        }
        config = _build_config(data)
        assert config['empresa']['google_maps_embed'] == 'https://maps.google.com/embed?pb=abc123'

    def test_leads_fields(self):
        data = {
            'worker_url': 'https://leads.example.workers.dev',
            'client_token': 'token-abc-123',
        }
        config = _build_config(data)
        assert config['leads']['worker_url'] == 'https://leads.example.workers.dev'
        assert config['leads']['client_token'] == 'token-abc-123'

    def test_empty_keywords_and_locations(self):
        data = {
            'keywords_manual': '',
            'locations': '',
        }
        config = _build_config(data)
        assert config['seo']['palavras_chave'] == []
        assert config['seo']['locais'] == []

    def test_keywords_dedup_with_whitespace(self):
        data = {
            'keywords_manual': 'Pet Shop\n  Banho e Tosa  \n\nPet Shop\n',
            'locations': 'Curitiba\n\n  \nSão José\n',
        }
        config = _build_config(data)
        # Manual keywords don't dedup in _build_config (dedup is in frontend)
        assert 'Pet Shop' in config['seo']['palavras_chave']
        assert 'Banho e Tosa' in config['seo']['palavras_chave']
        assert 'Curitiba' in config['seo']['locais']
        assert 'São José' in config['seo']['locais']
        # Empty lines should be filtered
        assert '' not in config['seo']['locais']
        assert '' not in config['seo']['palavras_chave']


class TestUploadCSV:
    """Testes do endpoint /api/upload-csv."""

    def test_upload_valid_csv(self, tmp_path):
        """Upload de CSV simples com keywords."""
        csv_content = "Keyword\nPet Shop Curitiba\nBanho e Tosa\nConsulta Veterinária\n"
        client = TestClient(app)

        resp = client.post(
            "/api/upload-csv",
            files={"file": ("keywords.csv", csv_content.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['count'] >= 1
        assert isinstance(data['keywords'], list)

    def test_upload_empty_file(self):
        """Upload de arquivo vazio."""
        client = TestClient(app)
        resp = client.post(
            "/api/upload-csv",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['count'] == 0


class TestDownloadEndpoint:
    """Testes do endpoint /api/download."""

    def test_path_traversal_blocked(self):
        """Path traversal deve retornar 400."""
        client = TestClient(app)
        # Passar .. sem barras evita o 404 de rota não encontrada do FastAPI
        resp = client.get("/api/download/..domain.com")
        assert resp.status_code == 400

    def test_nonexistent_file(self):
        """Arquivo inexistente deve retornar 404."""
        client = TestClient(app)
        resp = client.get("/api/download/naoexiste.com.br")
        assert resp.status_code == 404
