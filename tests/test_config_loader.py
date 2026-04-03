"""Testes para core/config_loader.py"""
import pytest
import yaml
from core.config_loader import load_config, get_phone_display, get_whatsapp_link
from core.exceptions import ConfigError


def _make_config(tmp_path, overrides=None):
    """Cria um config.yaml mínimo válido em tmp_path."""
    data = {
        "empresa": {
            "nome": "PisoPro",
            "dominio": "pisopro.com.br",
            "categoria": "Instalação de Piso",
            "telefone_whatsapp": "5511999990000",
        },
        "seo": {
            "palavras_chave": ["instalação de piso"],
            "locais": ["São Paulo"],
        },
    }
    if overrides:
        for key, value in overrides.items():
            data[key].update(value)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return str(path)


class TestLoadConfig:
    def test_loads_valid_config(self, tmp_path):
        path = _make_config(tmp_path)
        config = load_config(path)
        assert config["empresa"]["nome"] == "PisoPro"

    def test_raises_if_file_missing(self, tmp_path):
        with pytest.raises(ConfigError):
            load_config(str(tmp_path / "nao_existe.yaml"))

    def test_raises_if_nome_missing(self, tmp_path):
        data = {
            "empresa": {
                "dominio": "x.com",
                "categoria": "Piso",
                "telefone_whatsapp": "5511999990000",
            },
            "seo": {"palavras_chave": ["piso"], "locais": ["SP"]},
        }
        path = tmp_path / "config.yaml"
        path.write_text(yaml.dump(data), encoding="utf-8")
        with pytest.raises(ConfigError, match="empresa.nome"):
            load_config(str(path))

    def test_applies_defaults(self, tmp_path):
        path = _make_config(tmp_path)
        config = load_config(path)
        assert config["api"]["provider"] == "openrouter"
        assert config["empresa"]["cor_marca"] == "#2563EB"

    def test_raises_if_no_keywords(self, tmp_path):
        data = {
            "empresa": {
                "nome": "X",
                "dominio": "x.com",
                "categoria": "Piso",
                "telefone_whatsapp": "5511999990000",
            },
            "seo": {"palavras_chave": [], "locais": ["SP"]},
        }
        path = tmp_path / "config.yaml"
        path.write_text(yaml.dump(data), encoding="utf-8")
        with pytest.raises(ConfigError, match="palavra"):
            load_config(str(path))


class TestGetPhoneDisplay:
    def _cfg(self, phone):
        return {"empresa": {"telefone_whatsapp": phone, "telefone_ligar": phone}}

    def test_with_country_code_11_digits(self):
        result = get_phone_display(self._cfg("5511999990000"))
        assert result == "(11) 99999-0000"

    def test_without_country_code(self):
        result = get_phone_display(self._cfg("11999990000"))
        assert result == "(11) 99999-0000"


class TestGetWhatsappLink:
    def test_link_format(self):
        config = {"empresa": {"telefone_whatsapp": "5511999990000"}}
        link = get_whatsapp_link(config)
        assert link.startswith("https://wa.me/5511999990000")
        assert "text=" in link
