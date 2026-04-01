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

load_dotenv()

class GeminiImageClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY não configurada no .env")
        
        self.client = genai.Client(api_key=self.api_key)

    def generate_hero(self, categoria: str, nome: str, output_path: str, keywords: list = None, theme_mode: str = 'dark') -> bool:
        """
        Gera e salva a imagem. Retorna True se sucesso, False se falha.
        """
        servicos = ", ".join(keywords[:3]) if keywords else categoria
        
        if theme_mode == 'light':
            palette = "Color palette: bright, clean, airy whites and soft pastels with warm natural light."
        else:
            palette = "Color palette: dark gray, black, and subtle hints of professional colors."
        
        prompt = (
            f"Premium cinematic photography representing the final positive outcome, satisfaction, and elegance in the field of: {categoria}. "
            f"Show beautiful, clean, and positive concepts (e.g. happy clients, healthy pets, pristine environments). Do NOT show raw tools, surgery equipment, or messy work processes. "
            f"Lighting: Cinematic, dramatic, moody. Depth of field: strong bokeh effect on background. "
            f"Composition: CENTER the main subjects (people, animals, objects) in the horizontal middle of the frame. "
            f"The subjects must be clearly visible even if the image is cropped to a narrow vertical strip from the center. "
            f"Leave negative space in the UPPER portion of the image for text overlays. "
            f"{palette} "
            f"Style: High-end, premium corporate, elegant and modern lifestyle."
        )

        try:
            print(f"  📸 Solicitando imagem via SDK (Imagen 3) para marca: {nome}...")
            
            result = self.client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="16:9"
                )
            )

            for generated_image in result.generated_images:
                import io
                from PIL import Image
                
                # O SDK retorna a imagem customizada
                raw_bytes = generated_image.image.image_bytes
                
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Decodifica e força conversão para JPEG premium
                pil_img = Image.open(io.BytesIO(raw_bytes))
                pil_img.convert("RGB").save(output_path, format="JPEG", quality=90)
                
                print(f"  ✓ Imagem gerada com sucesso: {output_path}")
                return True
                
            print("  ❌ Nenhuma imagem retornada pela API.")
            return False

        except Exception as e:
            print(f"  ❌ Exceção ao gerar imagem: {e}")
            return False
