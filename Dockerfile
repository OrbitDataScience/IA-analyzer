# Use a imagem oficial do Python como base
FROM python:3.10-slim

# Instale dependências do sistema
RUN apt-get update && apt-get install -y gcc

# Copie o código da API para o contêiner
WORKDIR /app
COPY . .

# Instale as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponha a porta padrão do FastAPI
EXPOSE 8501

# Comando para iniciar o servidor
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8501"]
