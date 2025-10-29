FROM node AS frontend-builder
WORKDIR /frontend
COPY frontend/ ./
RUN npm install --verbose && npm run build --verbose

FROM python:3.11

WORKDIR /backend 

COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    pandoc \
    poppler-utils \
    nginx \
    && rm -rf /var/lib/apt/lists/*

RUN python -m nltk.downloader stopwords -d /usr/local/nltk_data
ENV NLTK_DATA=/usr/local/nltk_data

COPY . .
RUN pip install --no-cache-dir "uvicorn[standard]" gunicorn


ENV PYTHONUNBUFFERED=1

COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8080

CMD ["./docker-entrypoint.sh"]
