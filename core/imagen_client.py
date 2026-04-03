"""
Cliente Gemini/Imagen API para geração de backgrounds via prompt.
"""
import os
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv
import io
from core.logger import get_logger
from core.exceptions import ConfigError
logger = get_logger(__name__)

load_dotenv()

_SCENE_FEW_SHOT_EXAMPLES = """- Pet Shop / Banho e Tosa: "a happy, fluffy golden retriever dog sitting on a clean grooming table in a bright salon, soft warm lighting"
- Advocacia / Escritório de Advocacia: "open law book with an elegant wooden gavel on a polished dark desk, warm bokeh background in a prestigious office"
- Odontologia / Clínica Odontológica: "pristine white premium dental chair in a modern, bright, high-tech clinic, welcoming atmosphere"
- Restaurante / Gastronomia: "a beautifully plated gourmet dish on a rustic wooden table with elegant restaurant ambiance in the background"
- Academia / Personal Trainer: "shiny premium dumbbells and kettlebells lined up perfectly in a modern, high-end gym, strong dramatic lighting"
- Limpeza / Serviços de Limpeza: "a spotlessly clean, gleaming modern living room with a fresh, airy atmosphere and soft sunlight"
- Imobiliária / Corretora de Imóveis: "a beautiful luxury modern home exterior with a perfectly manicured green lawn, sunny day"
- Elétrica / Eletricista: "modern smart home electrical panel with glowing blue circuits in a pristine tech environment"
- Mecânica / Auto Center: "a gleaming luxury sports car freshly detailed in a modern, professional, high-end garage, cinematic lighting"
- Jardinagem / Paisagismo: "a beautifully landscaped lush green garden with vibrant flowers and a perfectly cut lawn, morning sunlight\""""


def _generate_scene_description(categoria: str, llm_client) -> str:
    """
    Usa o LLM com few-shot prompting para gerar uma descrição de cena fotográfica
    específica para o nicho do cliente.

    Retorna uma string com a cena, ou um fallback genérico se falhar.
    """
    system_prompt = (
        "You are a professional photography art director specializing in premium cinematic hero images for local service business websites. "
        "Your task is to write a single, precise English sentence describing the ideal photographic scene for a given business niche. "
        "CRITICAL RULE 1: The scene MUST strongly feature the primary NON-HUMAN subject of the niche to be instantly recognizable (e.g., a cute dog and cat for a petshop, a gleaming car for a mechanic, delicious food for a restaurant). DO NOT describe an empty room unless absolutely necessary. "
        "CRITICAL RULE 2: ABSOLUTELY NO PEOPLE, NO HUMANS, NO FACES anywhere in the scene. Do not mention humans at all. "
        "Output ONLY the scene description sentence. No explanations, no quotes, no extra text."
    )

    user_prompt = (
        f"Generate a cinematic photography scene description for this business niche: \"{categoria}\"\n\n"
        f"Use these examples as style reference:\n{_SCENE_FEW_SHOT_EXAMPLES}\n\n"
        f"Now generate ONE scene for: \"{categoria}\""
    )

    try:
        scene = llm_client.generate_text(system_prompt, user_prompt)
        if scene and len(scene.strip()) > 10:
            scene = scene.strip().strip('"').strip("'")
            logger.info("Cena gerada pelo LLM para '%s': %s", categoria, scene)
            return scene
    except Exception as e:
        logger.warning("Falha ao gerar cena via LLM: %s — usando fallback genérico", e)

    # Fallback genérico seguro
    return f"clean, elegant, professional environment and tools related to {categoria}"


class GeminiImageClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ConfigError("GEMINI_API_KEY não configurada no .env")

        self.client = genai.Client(api_key=self.api_key)

    def generate_hero(
        self,
        categoria: str,
        nome: str,
        output_path: str,
        keywords: list = None,
        theme_mode: str = 'dark',
        llm_client=None,
    ) -> bool:
        """
        Gera e salva a imagem hero do site.

        Args:
            categoria: Nicho do negócio (ex: "Desentupidora e Caça Vazamento")
            nome: Nome da empresa
            output_path: Caminho para salvar o JPEG
            keywords: Lista de palavras-chave do negócio
            theme_mode: 'dark' ou 'light'
            llm_client: Instância de OpenRouterClient para gerar cena via few-shot.
                        Se None, usa fallback genérico.

        Returns:
            True se a imagem foi gerada com sucesso, False caso contrário.
        """
        if theme_mode == 'light':
            palette = "Color palette: bright, clean, airy whites and soft pastels with warm natural light."
        else:
            palette = "Color palette: dark gray, black, and subtle hints of professional colors."

        # Gera cena específica via LLM (few-shot) ou usa fallback genérico
        if llm_client is not None:
            scene = _generate_scene_description(categoria, llm_client)
        else:
            scene = f"clean, elegant environment and tools for {categoria}"

        prompt = (
            f"Premium cinematic photography for a local business website hero image. "
            f"Business niche: {categoria}. "
            f"Scene: {scene}. "
            f"STRICT RULES — VIOLATION IS NOT ACCEPTABLE: "
            f"(1) ZERO TEXT anywhere in the image. No words, no letters, no captions, no watermarks. "
            f"(2) ABSOLUTELY NO PEOPLE, NO HUMANS, NO FACES in the picture. Show ONLY the environment, objects, tools, or animals. "
            f"Lighting: Cinematic, dramatic, moody. Strong bokeh on background. "
            f"Composition: ALL main subjects MUST be perfectly centered in the absolute MIDDLE of the frame. "
            f"Outer 20% left and right must be blurred background only. "
            f"{palette} "
            f"Style: High-end premium corporate photography, photo-realistic, elegant."
        )

        try:
            logger.info("Gerando imagem hero para '%s' (cena: %s)", nome, scene[:60])

            result = self.client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="1:1"
                )
            )

            for generated_image in result.generated_images:
                raw_bytes = generated_image.image.image_bytes
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                pil_img = Image.open(io.BytesIO(raw_bytes))
                pil_img.convert("RGB").save(output_path, format="JPEG", quality=90)
                logger.info("Imagem gerada: %s", output_path)
                return True

            logger.error("Nenhuma imagem retornada pela API")
            return False

        except Exception as e:
            logger.error("Exceção ao gerar imagem: %s", e)
            return False

