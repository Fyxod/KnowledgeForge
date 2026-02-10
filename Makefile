.PHONY: build run run-silent pull-mongo install-ollama set-models \
        ollama ollama-stop ollama-1 ollama-2

IMAGE_NAME := samsung
MONGO_IMAGE := mongo:latest

# High-level targets

build: docker-build pull-mongo install-ollama set-models
	@echo " Build pipeline completed successfully"

run:   docker-up
	@echo " Stack running (attached)"

run-silent: ollama docker-up-detached
	@echo " Stack running (detached)"

# Docker

docker-build:
	@echo " Building Docker image: $(IMAGE_NAME)"
	docker build -t $(IMAGE_NAME) .

pull-mongo:
	@echo "Pulling MongoDB image"
	docker pull $(MONGO_IMAGE)

docker-up:
	docker compose up

docker-up-detached:
	docker compose up -d

# Ollama

install-ollama:
	@echo " Installing Ollama"
	chmod +x scripts/install_ollama_Linux.sh
	./scripts/install_ollama_Linux.sh

set-models:
	@echo " Setting up Ollama models"
	chmod +x scripts/setmodel.sh
	./scripts/setmodel.sh

ollama:  ollama-1 ollama-2
	@echo " Ollama running on ports 11434 and 11435"

ollama-1:
	@echo " Starting Ollama on :11434"
	OLLAMA_HOST=0.0.0.0:11434 OLLAMA_KEEP_ALIVE=-1 \
	nohup ollama serve > logs/ollama-11434.log 2>&1 &

ollama-2:
	@echo " Starting Ollama on :11435"
	OLLAMA_HOST=0.0.0.0:11435 OLLAMA_KEEP_ALIVE=-1 \
	nohup ollama serve > logs/ollama-11435.log 2>&1 &

ollama-stop:
	@echo " Stopping all Ollama instances"
	pkill -f "ollama serve" || true
