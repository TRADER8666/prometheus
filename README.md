# Prometheus AI Workspace (MVP)

Prometheus is a **locally-hostable AI workspace** focused on efficient core capabilities:
- Chat with local LLMs via **Ollama**
- RAG / memory with **ChromaDB**
- Tool-augmented agent loop (code, file ops, web search, vector memory)
- Clean Svelte chat interface
- Zero-config install for Ubuntu/Debian (with optional NVIDIA acceleration)

## System Requirements

### Minimum
- Ubuntu/Debian (22.04+ recommended)
- 4 CPU cores
- 8 GB RAM
- 20 GB free disk

### Recommended
- 8+ CPU cores
- 16+ GB RAM
- NVIDIA GPU with 8+ GB VRAM (optional)

## Architecture Overview

- **Frontend (Svelte + Vite)**: port `3000`
- **Backend (FastAPI, Python 3.11)**: port `8000`
- **Ollama (host/native)**: port `11434`
- **SearXNG**: port `8080`
- **ChromaDB**: internal + host `8001`
- **Nginx reverse proxy**: port `80` (routes `/api` to backend, `/` to frontend)

```text
Browser -> Nginx:80
             |- /      -> Frontend:3000
             \- /api/* -> FastAPI:8000 -> Ollama(host:11434), ChromaDB, SearXNG
```

## Project Structure

```text
prometheus/
├── install.sh
├── docker-compose.yml
├── prometheus.service
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── agent.py
│   ├── tools/
│   │   ├── code_executor.py
│   │   ├── file_ops.py
│   │   ├── web_search.py
│   │   └── rag.py
│   └── cookbook.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── App.svelte
│   │   ├── main.js
│   │   └── components/
│   │       ├── Chat.svelte
│   │       ├── Sidebar.svelte
│   │       └── ModelSelector.svelte
├── nginx/
│   └── nginx.conf
└── README.md
```

## Quick Start

### 1) Clone repo
```bash
git clone https://github.com/TRADER8666/prometheus.git
cd prometheus
```

### 2) Run installer
```bash
chmod +x install.sh
./install.sh
```

Installer does:
1. Installs system packages (Ubuntu/Debian)
2. Installs Docker + Docker Compose
3. Installs **Ollama natively** (not containerized)
4. Detects GPU (NVIDIA priority, then AMD)
5. Pulls models:
   - `llama3.2:3b`
   - `qwen2.5-coder:1.5b`
   - `nomic-embed-text`
6. Sets up ChromaDB + app directories
7. Installs and enables `prometheus.service`
8. Opens firewall ports and configures LAN access

### 3) Open UI
- `http://<your-lan-ip>`

## API Endpoints (Core)

- `POST /api/chat`
- `POST /api/chat/stream` (SSE-style streaming)
- `GET /api/conversations`
- `POST /api/conversations`
- `DELETE /api/conversations/{id}`
- `GET /api/conversations/{id}/messages`
- `GET /api/models`
- `POST /api/models/pull`
- `DELETE /api/models/{model}`
- `GET /api/cookbook/recommendations`
- `POST /api/documents/upload`

## Tooling in Agent Loop

The backend supports tool execution syntax in user messages:

```text
[[tool:search {"query":"latest fastapi release"}]]
[[tool:file {"action":"list","path":"."}]]
[[tool:code {"code":"print(2+2)"}]]
[[tool:rag {"action":"query","text":"my uploaded docs"}]]
```

## Systemd Service

Service file: `prometheus.service`

Commands:
```bash
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
sudo systemctl status prometheus
sudo systemctl restart prometheus
```

## Development

### Backend local dev
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend local dev
```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Ollama not reachable
```bash
systemctl status ollama
curl http://127.0.0.1:11434/api/tags
```
If needed:
```bash
sudo systemctl restart ollama
```

### Docker permission denied
You may need to re-login after installer adds your user to `docker` group.

### GPU not used
- Check `nvidia-smi`
- Confirm drivers installed: `ubuntu-drivers devices`
- Ensure Ollama can see GPU after service restart

### SearXNG issues
Check logs:
```bash
docker compose logs searxng
```

### Full stack status
```bash
docker compose ps
docker compose logs --tail=100
```

## Security Note

This MVP is LAN-oriented and currently does **not** include authentication/authorization.
Do not expose directly to the public internet without adding auth, TLS hardening, and network controls.
