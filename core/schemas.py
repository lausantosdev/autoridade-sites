"""
Schemas Pydantic para geração de conteúdo SEO via Google Gemini.
Garante JSON válido por contrato — zero erros de parsing.
"""
from pydantic import BaseModel, Field


class PageContent(BaseModel):
    """Schema completo de uma página SEO. Usado como response_schema no Gemini."""

    # META TAGS
    titulo: str = Field(description="Título SEO: 8-12 palavras, keyword + local + empresa")
    meta_description: str = Field(description="25-30 palavras, chamativo, com keyword + local")
    meta_keywords: str = Field(description="10-15 termos separados por vírgula")

    # HERO
    hero_titulo_linha_1: str = Field(description="MÁXIMO 3 palavras — início da frase")
    hero_titulo_destaque: str = Field(description="2-4 palavras — keyword em destaque")
    hero_titulo_linha_3: str = Field(description="2-4 palavras — fecha frase com local")
    hero_subtitulo: str = Field(description="MÁXIMO 20 palavras — benefício + empresa + local")

    # DIFERENCIAIS
    diferencial_1_titulo: str = Field(description="3-5 palavras — vantagem competitiva genérica")
    diferencial_1_descricao: str = Field(description="Máx 15 palavras — frase curta explicando")
    diferencial_1_icone: str = Field(description="Classe FontAwesome 6 Free Solid, ex: fas fa-star")
    diferencial_2_titulo: str
    diferencial_2_descricao: str
    diferencial_2_icone: str
    diferencial_3_titulo: str
    diferencial_3_descricao: str
    diferencial_3_icone: str

    # AUTORIDADE
    autoridade_titulo: str = Field(description="6-9 palavras sobre a empresa + local")
    autoridade_manifesto: str = Field(description="40-60 palavras — profissional e honesto")

    # MEGA CTA
    cta_titulo: str = Field(description="4-6 palavras urgentes, inclui keyword ou local")
    cta_subtitulo: str = Field(description="8-12 palavras, complementa o CTA")

    # FAQ
    faq_h2: str = Field(description="4-6 palavras, ex: Perguntas Frequentes Sobre [keyword]")
    faq_1_pergunta: str
    faq_1_resposta: str = Field(description="40-60 palavras — resposta direta e útil")
    faq_2_pergunta: str
    faq_2_resposta: str = Field(description="40-60 palavras — objeção de compra")
    faq_3_pergunta: str
    faq_3_resposta: str = Field(description="40-60 palavras — dúvida prática")

    # SEO EDITORIAL (6 seções)
    seo_h2_1: str = Field(description="H2 informacional: 6-10 palavras")
    seo_p1: str = Field(description="130-160 palavras: define serviço, importância no local")
    seo_h2_2: str = Field(description="H2 processo: 6-10 palavras")
    seo_p2: str = Field(description="130-160 palavras: processo passo a passo")
    seo_h2_3: str = Field(description="H2 urgência: 6-10 palavras")
    seo_p3: str = Field(description="130-160 palavras: sinais que exigem o serviço")
    seo_h2_4: str = Field(description="H2 comparação: 6-10 palavras")
    seo_p4: str = Field(description="130-160 palavras: profissional vs caseiro")
    seo_h2_5: str = Field(description="H2 autoridade local: 6-10 palavras")
    seo_p5: str = Field(description="130-160 palavras: autoridade em local, com links internos")
    seo_h2_6: str = Field(description="H2 ação: 6-10 palavras")
    seo_p6: str = Field(description="130-160 palavras: próximos passos, CTA suave")
