.PHONY: build run run-silent pull-mongo docker-build docker-smoke \
        ollama ollama-stop ollama-1 ollama-2

IMAGE_NAME := knowledgeforge
MONGO_IMAGE := mongo:8.0.28-noble@sha256:346f9f37eb0f1b75600929979a8f62372e6c717e58a291736db09188acaad0fe

# High-level targets

build: docker-build pull-mongo
	@echo " Build pipeline completed successfully"

run:   docker-up
	@echo " Stack running (attached)"

run-silent: ollama docker-up-detached
	@echo " Stack running (detached)"

# Docker

docker-build:
	@echo " Building Docker image: $(IMAGE_NAME)"
	docker build --pull -t $(IMAGE_NAME):latest .

pull-mongo:
	@echo "Pulling MongoDB image"
	docker pull $(MONGO_IMAGE)

docker-up:
	docker compose up

docker-up-detached:
	docker compose up -d --wait

docker-smoke:
	./scripts/docker-smoke.sh

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
	mkdir -p logs
	OLLAMA_HOST=0.0.0.0:11434 OLLAMA_KEEP_ALIVE=-1 \
	nohup ollama serve > logs/ollama-11434.log 2>&1 &

ollama-2:
	@echo " Starting Ollama on :11435"
	mkdir -p logs
	OLLAMA_HOST=0.0.0.0:11435 OLLAMA_KEEP_ALIVE=-1 \
	nohup ollama serve > logs/ollama-11435.log 2>&1 &

ollama-stop:
	@echo " Stopping all Ollama instances"
	pkill -f "ollama serve" || true
