# Prometheus v1.0 — Local AI Workspace

Prometheus is a complete, locally-hostable AI workspace that combines:
- conversational AI + tool use
- visual AI
- orchestration (DAG + swarm)
- productivity suite (notes, kanban, bookmarks)
- scheduler automation
- voice I/O (Whisper STT + Piper TTS)

---

## Complete Feature List

### AI Core
- Local chat via Ollama
- Tool-augmented responses (code/file/search/rag)
- Multi-model router (coding / vision / reasoning / general)
- RAG memory with ChromaDB

### Vision
- Object detection (YOLO)
- Image generation (Stable Diffusion)
- Image editing / inpainting
- Vision analysis via Ollama vision models (e.g., llava)
- OCR text extraction

### Orchestration
- LLM-assisted task planning to DAG
- Parallel DAG execution with retries/backoff
- Swarm coordinator (master/worker)
- Real-time DAG updates via WebSocket (`/ws/dag`)
- MCP-compatible tool listing/execution APIs

### Productivity Suite
- **Notes**: markdown editor, tags, full-text search, export to `.md`
- **Kanban**: boards/columns/cards, drag-and-drop ordering, move across columns
- **Bookmarks**: folders/tags, search, import/export JSON, browser auto-save endpoint

### Scheduler
- APScheduler-based cron jobs
- Natural-language schedule shortcuts (e.g., "every morning at 8 AM")
- Job history/logs
- Built-in actions:
  - email summary (placeholder local mode)
  - daily briefing
  - backup data
  - system health check
  - custom agent task

### Voice & Audio
- Whisper speech-to-text (`/api/voice/transcribe`)
- Piper text-to-speech (`/api/voice/speak`)
- Voice command integration (`/ws/voice`)

---

## Architecture Diagram

```text
Browser (Svelte UI)
  ├─ Chat / Vision / Orchestration / Productivity / Scheduler / Voice
  └─ WebSockets (DAG + Voice)

Nginx :80
  ├─ /          -> Frontend :3000
  └─ /api/*     -> FastAPI :8000

FastAPI Backend
  ├─ Agent + Tool Runtime
  ├─ Orchestration Engine (planner + DAG + swarm + routing)
  ├─ Productivity Services (notes/kanban/bookmarks)
  ├─ Scheduler Service (APScheduler + croniter)
  ├─ Voice Services (Whisper + Piper)
  └─ SQLite (WAL)

External/Side Services
  ├─ Ollama :11434
  ├─ ChromaDB :8001
  └─ SearXNG :8080
```

---

## Installation (One Command)

```bash
git clone https://github.com/TRADER8666/prometheus.git
cd prometheus
chmod +x install.sh
./install.sh
```

Installer provisions:
- Docker + Compose
- host-native Ollama + model pulls (`llama3.2:3b`, `qwen2.5-coder:1.5b`, `nomic-embed-text`, `llava`)
- ffmpeg + audio dependencies
- AI Python dependencies (vision/orchestration/voice)
- Playwright Chromium
- Whisper model preload (`small`)
- Piper voice asset download
- systemd + LAN setup

---

## User Guide

### Sections
- **Chat**: ask questions, attach images, voice dictation, optional TTS playback
- **Orchestration**: generate editable execution plan, run DAG, monitor progress live
- **Vision**: detect/generate/edit/OCR/analyze images
- **Notes**: create/search/tag/export markdown notes
- **Kanban**: manage tasks visually and reorder via drag-and-drop
- **Bookmarks**: organize URLs by folders/tags
- **Scheduler**: create recurring automation jobs and inspect run history

---

## API Documentation (Key Endpoints)

### Core Chat
- `POST /api/chat`
- `POST /api/chat/stream`

### Vision
- `POST /api/upload_image`
- `GET /api/images/{filename}`
- `POST /api/detect_objects`
- `POST /api/generate_image`
- `POST /api/edit_image`
- `POST /api/analyze_image`
- `POST /api/extract_text`

### Orchestration
- `POST /api/plan`
- `POST /api/execute_dag`
- `GET /api/dag/{task_id}`
- `WS /ws/dag`

### MCP
- `GET /api/mcp/tools`
- `POST /api/mcp/execute`
- `POST /api/mcp/rpc`

### Notes
- `GET /api/notes`
- `POST /api/notes`
- `GET /api/notes/{id}`
- `PUT /api/notes/{id}`
- `DELETE /api/notes/{id}`
- `POST /api/notes/{id}/export`

### Kanban
- `GET/POST /api/kanban/boards`
- `PUT/DELETE /api/kanban/boards/{id}`
- `GET/POST /api/kanban/columns`
- `PUT/DELETE /api/kanban/columns/{id}`
- `GET/POST /api/kanban/cards`
- `PUT/DELETE /api/kanban/cards/{id}`
- `POST /api/kanban/cards/{id}/move`

### Bookmarks
- `GET/POST /api/bookmarks`
- `PUT/DELETE /api/bookmarks/{id}`
- `POST /api/bookmarks/auto-save`
- `GET /api/bookmarks/export`
- `POST /api/bookmarks/import`

### Scheduler
- `GET/POST /api/scheduler/jobs`
- `PUT/DELETE /api/scheduler/jobs/{id}`
- `GET /api/scheduler/history`

### Voice
- `POST /api/voice/transcribe`
- `POST /api/voice/speak`
- `WS /ws/voice`

---

## Development

### Backend
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Troubleshooting

### Ollama not reachable
```bash
curl http://127.0.0.1:11434/api/tags
systemctl status ollama
```

### Whisper fails
- ensure `ffmpeg` is installed
- verify audio format (wav/webm/mp3)

### Piper TTS fails
- ensure `piper` binary is installed and in PATH
- verify voice file path (default: `/opt/prometheus/voices/en_US-lessac-medium.onnx`)

### Scheduler jobs not running
- check `GET /api/scheduler/jobs`
- check `GET /api/scheduler/history`
- verify cron syntax

### Kanban drag-and-drop issues
- check frontend dependencies installed (`svelte-dnd-action`)

---

## UI/UX Notes

- Unified dark theme via `frontend/src/styles/theme.css`
- Responsive section layouts for mobile/tablet
- Loading/error states across major panels
- Navigation includes breadcrumbs + icon-based section menu

---

## Security

Prometheus is optimized for local/LAN use by default.
Before exposing publicly, add:
- authentication + authorization
- TLS
- rate limiting + security headers
- stricter CORS and network controls
