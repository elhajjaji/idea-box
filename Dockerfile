FROM python:3.9-slim-buster

# Labels d'information sur l'image (correspondant à l'image existante)
LABEL maintainer="el hajjaji Abderrahman <elhajjaji@gmail.com>"
LABEL description="Plateforme collaborative de gestion d'idées (FastAPI, MongoDB). Gestion de sujets, idées, votes, rôles, superadmin, gestionnaire, invités. Déploiement Docker ready."
LABEL version="1.0"
LABEL author="el hajjaji Abderrahman"
LABEL contact="elhajjaji@gmail.com"
LABEL created="2025-07-10"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
