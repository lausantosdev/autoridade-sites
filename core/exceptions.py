"""
Exceções customizadas do SiteGen.

Hierarquia:
    SiteGenError
    ├── ConfigError      — config.yaml inválido ou campo obrigatório ausente
    ├── APIError         — falha na comunicação com a API (OpenRouter/Gemini)
    ├── TemplateError    — template não encontrado ou placeholders não resolvidos
    └── ValidationError  — site gerado não passou na validação de qualidade
"""


class SiteGenError(Exception):
    """Base para todos os erros do SiteGen."""


class ConfigError(SiteGenError):
    """Config.yaml inválido ou campo obrigatório ausente."""


class APIError(SiteGenError):
    """Falha na comunicação com a API (OpenRouter/Gemini)."""


class TemplateError(SiteGenError):
    """Template não encontrado ou com placeholders não resolvidos."""


class ValidationError(SiteGenError):
    """Site gerado não passou na validação de qualidade."""
