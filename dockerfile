# Stage 1: Build frontend
FROM node AS frontend-builder

WORKDIR /frontend
COPY agla-hissa/ ./
RUN npm install && npm run build


# Stage 2: Build backend and final container
FROM python:3.11-slim

# Install backend dependencies
WORKDIR /backend
COPY req.txt .
RUN pip install --no-cache-dir -r req.txt


# Copy FastAPI app
COPY app/ ./app

# Copy built frontend
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Install nginx
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*
COPY . .
# Copy entrypoint
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8080

CMD ["./docker-entrypoint.sh"]
