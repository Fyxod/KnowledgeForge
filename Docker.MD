<!-- markdownlint-disable MD013 -->

# Running KnowledgeForge with Docker

The Compose stack builds the complete KnowledgeForge application and runs it with MongoDB. The application image contains the production frontend, FastAPI backend, Nginx reverse proxy, OCR system packages, CPU-compatible PyTorch, and pre-cached retrieval models.

## Prerequisites

- Docker Engine 24+ with Docker Compose v2
- At least 16 GB of free disk space for the initial build and model layers
- Ollama endpoints available on the host at ports `11434` and `11435` for AI-backed features

The application and database start without Ollama, so health, authentication, navigation, and document management remain independently testable. Queries and visual processing require the configured model endpoints.

## Start the stack

Create the runtime environment file:

```powershell
Copy-Item .env.docker .env
```

```bash
cp .env.docker .env
```

Replace `SECRET_KEY` with a unique random value, then build and start:

```bash
docker compose build --pull
docker compose up -d --wait
```

Open `http://localhost:8080`. The backend is also exposed directly at `http://localhost:8000`, with OpenAPI documentation at `http://localhost:8000/docs`.

## Verify the running stack

```bash
./scripts/docker-smoke.sh
```

The smoke test verifies:

- the direct backend health endpoint;
- the same API through Nginx;
- frontend static assets and SPA route fallback;
- user registration and login through MongoDB;
- the Socket.IO reverse-proxy path.

Inspect status and logs with:

```bash
docker compose ps
docker compose logs -f app
```

## Host model endpoints

The default `.env.docker` sets `LOCAL_BASE_URL=http://host.docker.internal`. Compose adds the portable `host-gateway` mapping on Linux, while Docker Desktop provides the same hostname on Windows and macOS.

Run the two Ollama listeners on the host:

```bash
OLLAMA_HOST=0.0.0.0:11434 OLLAMA_KEEP_ALIVE=-1 ollama serve
```

```bash
OLLAMA_HOST=0.0.0.0:11435 OLLAMA_KEEP_ALIVE=-1 ollama serve
```

## CPU and GPU embedding modes

The default image installs the official CPU wheels for PyTorch 2.10.0 and uses `EMBEDDINGS_DEVICE=auto`. This makes the Compose stack portable and keeps Ollama responsible for model inference.

To build with another official PyTorch wheel index, provide `TORCH_INDEX_URL` during the build and configure the Compose service with the corresponding GPU access. For example:

```bash
TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128 docker compose build --pull
```

Then set `EMBEDDINGS_DEVICE=cuda` only when the container has a working CUDA runtime.

## Image maintenance

The application uses versioned Node, Python, PyTorch, and MongoDB releases instead of floating `latest` tags. The Docker workflow rebuilds and smoke-tests the full stack for every relevant change, while Dependabot checks Docker and GitHub Actions dependencies weekly.

Force a clean refresh at any time:

```bash
docker compose build --pull --no-cache
docker compose up -d --wait --force-recreate
./scripts/docker-smoke.sh
```

## Stop the stack

```bash
docker compose down
```

MongoDB data remains in the named `mongo_data` volume and application data remains in `./data`. To remove containers and the MongoDB volume together:

```bash
docker compose down --volumes
```
