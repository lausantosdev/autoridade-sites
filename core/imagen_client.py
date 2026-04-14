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

_SCENE_FEW_SHOT_EXAMPLES = """- Pet Shop / Banho e Tosa: "a cheerful, colorful pet boutique interior with walls decorated with illustrated paw prints, colorful pet accessories hanging on display, warm wood shelves with neatly arranged pet products, soft warm lighting — NO real animals, NO cages, NO tools"
- Clínica Veterinária / Veterinário: "a warm, charming veterinary clinic waiting room with cheerful illustrated animal murals on the walls, cozy wooden benches with colorful pet-themed cushions, small ceramic pet bowls on display shelves, lush tropical plants and warm soft lighting throughout — welcoming, pet-friendly, NO real animals, NO surgical instruments, NO clinical equipment"
- Advocacia / Escritório de Advocacia: "prestigious warm library with leather armchairs and golden ambient lighting — NO documents, NO papers"
- Odontologia / Clínica Odontológica: "spa-like waiting room, plush chairs, indoor plants, warm lighting — NO dental chairs, NO dental tools"
- Restaurante / Gastronomia: "a beautifully set table in a warm, elegant restaurant with candles and subtle ambient lighting — NO kitchen tools"
- Academia / Personal Trainer: "high-end premium wellness studio with soft indirect lighting and a welcoming atmosphere — NO weights, NO machines"
- Limpeza / Serviços de Limpeza: "a spotlessly clean, gleaming modern living room with a fresh, airy atmosphere and soft sunlight — NO mops, NO buckets, NO cleaning products"
- Imobiliária / Corretora de Imóveis: "a beautiful luxury modern home exterior with a perfectly manicured green lawn, sunny day"
- Elétrica / Eletricista: "modern smart home interior with warm LED accent lighting, minimalist decor, elegant finishes — NO wires, NO electrical panels, NO tools"
- Mecânica / Auto Center: "gleaming luxury car in a pristine automotive showroom with polished floors and dramatic spotlights — NO tools, NO grease, NO engine parts"
- Jardinagem / Paisagismo: "a beautifully landscaped lush green garden with vibrant flowers, stone pathways and morning sunlight — NO garden tools, NO equipment"
- Desentupidora / Caça Vazamento / Hidráulica: "a pristine, spotlessly clean modern bathroom with gleaming white tiles, polished fixtures and soft warm lighting — NO pipes, NO tools, NO water damage"
- Assistência Técnica / Eletrônicos / Informática: "a sleek, minimalist technology showroom with ambient backlighting and clean display surfaces — NO open devices, NO circuit boards, NO tools"
- Construção Civil / Reformas / Pintura: "a beautifully finished luxury living room with polished floors, high ceilings and premium interior design — NO raw materials, NO tools, NO construction debris"
- Contabilidade / Finanças: "an elegant, minimalist executive office with a clean desk, warm light and city view through floor-to-ceiling windows — NO papers, NO folders"
- Saúde / Clínica Médica / Estética: "a serene, spa-like premium clinic reception with marble surfaces, orchids and soft diffused lighting — NO medical equipment, NO clinical instruments"
"""


def _generate_scene_description(categoria: str, llm_client, keywords: list = None) -> str:
    """
    Usa o LLM com few-shot prompting para gerar uma descrição de cena fotográfica
    específica para o nicho do cliente.

    keywords: lista de serviços reais do negócio — usados para desambiguar categorias
    amplas como 'Assistência Técnica' e garantir que a cena seja relevante.

    Retorna uma string com a cena, ou um fallback genérico se falhar.
    """
    system_prompt = (
        "You are a professional photography art director specializing in premium cinematic hero images for local service business websites. "
        "Your task is to write a single, precise English sentence describing the ideal photographic scene for a given business niche. "
        "CRITICAL RULE 1: Focus EXCLUSIVELY on the ASPIRATIONAL OUTCOME or the WELCOMING ENVIRONMENT. "
        "Show the RESULT the customer desires or the premium atmosphere they will experience. "
        "ABSOLUTE PROHIBITION — applies to ALL niches without exception: NEVER describe or suggest tools, instruments, "
        "equipment, machines, raw materials, supplies, chemicals, products, open devices, construction materials, "
        "pipes, wires, cables, paperwork, medical/veterinary/dental instruments, or any work-in-progress. "
        "This includes: scalpels, syringes, wrenches, drills, mops, buckets, circuit boards, engine parts, scaffolding, "
        "paint cans, legal folders, or any object associated with the physical work of the trade. "
        "ALWAYS show: interiors with warm lighting, premium finishes, elegant decor, clean spaces, aspirational results. "
        "CRITICAL RULE 2: ABSOLUTELY NO PEOPLE, NO HUMANS, NO FACES anywhere in the scene. Do not mention humans at all. "
        "Output ONLY the scene description sentence. No explanations, no quotes, no extra text."
    )

    # Incluir keywords para desambiguar categorias amplas (ex: 'Assistência Técnica' → clarifica que é de eletrodomésticos)
    keywords_context = ""
    if keywords:
        keywords_context = f"\nThe business specifically offers: {', '.join(keywords[:5])}"

    user_prompt = (
        f"Generate a cinematic photography scene description for this business niche: \"{categoria}\"{keywords_context}\n\n"
        f"Use these examples as style reference:\n{_SCENE_FEW_SHOT_EXAMPLES}\n\n"
        f"Now generate ONE scene for: \"{categoria}\"{keywords_context}"
    )

    try:
        scene = llm_client.generate_text(system_prompt, user_prompt)
        if scene and len(scene.strip()) > 10:
            scene = scene.strip().strip('"').strip("'")
            logger.info("Cena gerada pelo LLM para '%s': %s", categoria, scene)
            return scene
    except Exception as e:
        logger.warning("Falha ao gerar cena via LLM: %s — usando fallback genérico", e)

    # Fallback seguro: mantém contexto do nicho mas com restrições explícitas
    return (
        f"a clean, elegant and premium welcoming reception area evoking the professional "
        f"atmosphere of a {categoria} business — warm ambient lighting, minimal modern decor, "
        f"lush indoor plants, polished surfaces — absolutely no tools, instruments, equipment, "
        f"machines, products, or work-related objects visible anywhere"
    )


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

        # Gera cena específica via LLM (few-shot + keywords) ou usa fallback genérico
        if llm_client is not None:
            scene = _generate_scene_description(categoria, llm_client, keywords)
        else:
            scene = f"clean, welcoming environment for {categoria}"

        prompt = (
            f"Premium cinematic photography for a local business website hero image. "
            f"Business niche: {categoria}. "
            f"Scene: {scene}. "
            f"STRICT RULES — VIOLATION IS NOT ACCEPTABLE: "
            f"(1) ABSOLUTELY ZERO TEXT anywhere in the image. No words, no letters, no captions, no watermarks, no signs, no logos, no brand names, no store names, no writing of any kind. The image must be 100% text-free. "
            f"(2) ABSOLUTELY NO PEOPLE, NO HUMANS, NO FACES anywhere in the image. "
            f"(3) ABSOLUTELY NO TOOLS, EQUIPMENT OR WORK OBJECTS of any kind — this means: "
            f"no surgical/dental/veterinary instruments, no wrenches, drills, pliers or hand tools, "
            f"no plumbing pipes or fittings, no electrical wires or panels, no open electronic devices or circuit boards, "
            f"no construction materials, scaffolding or raw finishes, no cleaning products or buckets, "
            f"no engine parts, no chemical containers, no legal documents or folders. "
            f"Focus ONLY on the WELCOMING ATMOSPHERE and ASPIRATIONAL RESULT: elegant interiors, premium decor, warm light. "
            f"Lighting: Cinematic, warm, inviting. Strong bokeh on background. "
            f"Composition: Main subject in the center 50% of the frame. Outer 25% on each side must be heavily blurred (safe crop zone). "
            f"{palette} "
            f"Style: High-end premium lifestyle photography, warm, photo-realistic, elegant."
        )

        try:
            logger.info("Gerando imagem hero para '%s' (cena: %s)", nome, scene[:60])

            result = self.client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",  # API retorna JPEG; convertemos para WebP abaixo
                    aspect_ratio="16:9",
                    person_generation="DONT_ALLOW"
                )
            )

            for generated_image in result.generated_images:
                raw_bytes = generated_image.image.image_bytes
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                pil_img = Image.open(io.BytesIO(raw_bytes))
                pil_img.convert("RGB").save(output_path, format="WEBP", quality=80)
                logger.info("Imagem gerada: %s", output_path)
                return True

            logger.error("Nenhuma imagem retornada pela API")
            return False

        except Exception as e:
            logger.error("Exceção ao gerar imagem: %s", e)
            return False

