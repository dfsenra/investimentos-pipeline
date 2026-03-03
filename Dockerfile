FROM python:3.12-slim

#Mantenedor da imagem
LABEL maintainer="Douglas Senra <dfsenra@gmail.com>"

# Diretório de trabalho dentro do container
WORKDIR /app

ENV PYTHONPATH=/app

# Evita arquivos .pyc e garante logs no stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copia e instala dependências primeiro (melhor cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o projeto
COPY . .
# Garante CSV na pasta /data
COPY data/ /data/


# Streamlit usa essa porta por padrão
EXPOSE 8501

# Executa o dashboard
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
