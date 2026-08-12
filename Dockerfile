# syntax=docker/dockerfile:1.7

FROM node:22.23.1-bookworm-slim@sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3 AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3 AS runtime

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

ENV DEBIAN_FRONTEND=noninteractive \
    HF_HOME=/opt/knowledgeforge/huggingface \
    NLTK_DATA=/usr/local/nltk_data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /backend

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        fonts-dejavu-core \
        fonts-liberation \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libreoffice-impress \
        libreoffice-writer \
        nginx \
        pandoc \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

COPY requirements-docker.txt ./

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        torch==2.10.0 \
        torchvision==0.25.0 \
        torchaudio==2.10.0 \
        --index-url "${TORCH_INDEX_URL}" \
    && python -m pip install --no-cache-dir -r requirements-docker.txt \
    && python -m pip check

RUN python -m nltk.downloader stopwords punkt_tab -d "${NLTK_DATA}" \
    && python -m spacy download en_core_web_sm \
    && python -c "from sentence_transformers import CrossEncoder, SentenceTransformer; SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

COPY . .
COPY --from=frontend-builder /frontend/dist/ /usr/share/nginx/html/
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /usr/local/bin/knowledgeforge-entrypoint

RUN chmod +x /usr/local/bin/knowledgeforge-entrypoint \
    && mkdir -p /backend/data \
    && python -m compileall -q agent app core

EXPOSE 8000 8080

HEALTHCHECK CMD ["curl", "--fail", "--silent", "--show-error", "http://127.0.0.1:8000/health/"]

ENTRYPOINT ["/usr/local/bin/knowledgeforge-entrypoint"]
