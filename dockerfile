FROM node AS frontend-builder
WORKDIR /frontend
COPY agla-hissa/ ./
RUN npm install && npm run build

FROM python:3.11-slim

WORKDIR /backend 

COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    poppler-utils \
    nginx \
    && rm -rf /var/lib/apt/lists/*


COPY . .

COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8080

CMD ["./docker-entrypoint.sh"]
