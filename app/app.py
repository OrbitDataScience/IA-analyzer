import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tempfile
import time
import google.generativeai as genai

#uvicorn app:app
#Para iniciar o servidor


#Enviar um json


# Configura a API do Gemini

# Inicializa o FastAPI
app = FastAPI(title="Video Analysis API", version="1.0")

# Configuração do modelo generativo
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Modelo para entrada de dados
class VideoLink(BaseModel):
    link: str


def download_video(link):
    if "tiktok" in link:
        url = "https://social-media-video-downloader.p.rapidapi.com/smvd/get/tiktok"
        rede_social = "TikTok"
    elif "instagram" in link:
        url = "https://social-media-video-downloader.p.rapidapi.com/smvd/get/instagram"
        rede_social = "Instagram"
    elif "facebook" in link:
        url = "https://social-media-video-downloader.p.rapidapi.com/smvd/get/facebook"
        rede_social = "Facebook"
    else:
        raise ValueError("Link inválido. Suporte apenas para TikTok, Instagram ou Facebook.")

    querystring = {"url": link}
    headers = {
        "x-rapidapi-key": "dc20fe78e2msh6fe9f52b9cffde8p1bd98djsn9b9256bdb611",
        "x-rapidapi-host": "social-media-video-downloader.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Erro ao baixar o vídeo.")

    descricao = response.json().get('title', "Sem descrição")
    video_url = None

    for item in response.json().get('links', []):
        if item['quality'] in ['video_hd_original_0', 'video_hd_original', 'video_hd_0']:
            video_url = item['link']
            break

    if not video_url:
        raise HTTPException(status_code=500, detail="Não foi possível obter o link do vídeo em alta definição.")

    video_response = requests.get(video_url, stream=True)
    temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")

    with open(temp_video.name, "wb") as file:
        for chunk in video_response.iter_content(chunk_size=1024):
            file.write(chunk)

    return temp_video.name, rede_social, descricao


def upload_to_gemini(path):
    video_file = genai.upload_file(path=path)
    while video_file.state.name == "PROCESSING":
        time.sleep(10)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise HTTPException(status_code=500, detail="Falha no processamento do vídeo no Gemini.")

    return video_file


@app.post("/analyze-video/")
async def analyze_video(video_link: VideoLink):
    try:
        # Baixar o vídeo a partir do link
        video_path, rede_social, descricao = download_video(video_link.link)

        # Configurar o prompt de acordo com a rede social
        if rede_social == "TikTok":
            prompt = f"""
                Você é um analista de videos que responder algumas perguntas sobre um vídeo extraído das redes sociais da marca ‘Ambev’:

                Responda as perguntas 1, 2, 3, 4, 5, 7 e 9 apenas com 'Sim' ou 'Não'

                Retorne em forme de tabela as perguntas e suas respostas.

                1 - O vídeo tem descrição ?

                2 - O vídeo contém Sound On ?

                3 - O vídeo contém a marca ’Ambev’ em evidência no começo do conteúdo ?

                4 - O vídeo contem uso do Disclaimer Legal (Exemplo: Beba com moderação) ?

                5 - O vídeo tem a Presença de assets de marca 'Ambev' (Logo, Brands Distintives Assets, Materiais Funcionais como Copo, Garrafa, Influenciadores) ?

                6 - Qual a duração do vídeo ?

                7 - O vídeo tem Momento Bang (Uso de Transição, Trends Criativas, Quebra de Expectativa) ?

                8 - Qual a dimensão do Formato da Publicação (1:1, 4:5, 3:4, 9:16, ...) ?

                9 - O vídeo respeita as Safe Zones nas imagens (não incluir elementos visuais nas bordas do conteúdo onde ficam os botões como like e comentários) ?
                """
        else:
            prompt = f"""
                Você é um analista de videos que responder algumas perguntas sobre um vídeo extraído das redes sociais da marca ‘Ambev’:

                Responda as perguntas 1, 2, 3, 4 e 7 apenas com 'Sim' ou 'Não'

                Retorne em forme de tabela as perguntas e suas respostas.

                1 - O vídeo tem descrição ?

                2 - O vídeo contém a marca ’Ambev’ em evidência no começo do conteúdo ?

                3 - O vídeo contem uso do Disclaimer Legal (Exemplo: Beba com moderação) ?

                4 - O vídeo tem a Presença de assets de marca 'Ambev' (Logo, Brands Distintives Assets, Materiais Funcionais como Copo, Garrafa, Influenciadores) ?

                5 - Qual a duração do vídeo ?

                6 - Qual a dimensão do Formato da Publicação (1:1, 4:5, 3:4, 9:16, ...) ?

                7 - O vídeo respeita as Safe Zones nas imagens (não incluir elementos visuais nas bordas do conteúdo onde ficam os botões como like e comentários) ?
                """

        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-002",
            generation_config=generation_config,
            system_instruction=prompt,
        )

        # Fazer upload do vídeo para o Gemini
        file = upload_to_gemini(video_path)

        # Obter a resposta do modelo
        response = model.generate_content([file, prompt], request_options={"timeout": 600})

        # Retornar o resultado
        return {
            "message": "Análise concluída com sucesso!",
            "description": descricao,
            "rede_social": rede_social,
            "response": response.text,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar o vídeo: {e}")
