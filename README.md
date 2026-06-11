# Prometheus AI Workspace

Prometheus is a locally-hostable AI workspace with:
- local LLM chat via Ollama
- RAG memory via ChromaDB
- vision tools (detect/generate/edit/OCR/analyze)
- **advanced orchestration** (DAG planning + execution + swarm + model routing + MCP)

---

## Core Capabilities

### 1) Chat + Tool Use
- chat endpoint with tool-invocation syntax
- code/file/search/rag tools
- productivity tools: git/browser/email/calendar/utilities

### 2) Vision
- YOLO object detection
- Stable Diffusion image generation
- Stable Diffusion inpainting
- Ollama vision analysis (`llava`)
- OCR (`easyocr`)

### 3) Orchestration Intelligence Layer
- DAG engine with:
  - topological execution
  - node states: `PENDING -> IN_PROGRESS -> COMPLETED/FAILED/SKIPPED`
  - retry with exponential backoff
  - parallel execution of independent nodes
  - conditional branch support
- Swarm coordinator with master/worker model and AMP (Agent Message Protocol)
- Planner that decomposes natural language into DAG steps
- Multi-model router for coding/general/reasoning/vision tasks
- MCP server/client support
- Real-time DAG updates via WebSocket

---

## Architecture

- Frontend (Svelte + Vite): `3000`
- Backend (FastAPI): `8000`
- Ollama (host-native): `11434`
- ChromaDB: `8001`
- SearXNG: `8080`
- Nginx reverse proxy: `80`

Nginx routing:
- `/` -> frontend
- `/api/*` -> backend

---

## API Endpoints

### Chat + Core
- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/conversations`
- `POST /api/conversations`
- `DELETE /api/conversations/{id}`
- `GET /api/conversations/{id}/messages`

### Model / Cookbook
- `GET /api/models`
- `POST /api/models/pull`
- `DELETE /api/models/{model}`
- `GET /api/cookbook/recommendations`
- `POST /api/models/recommend`

### Vision
- `POST /api/upload_image`
- `GET /api/images/{filename}`
- `POST /api/detect_objects`
- `POST /api/generate_image`
- `POST /api/edit_image`
- `POST /api/analyze_image`
- `POST /api/extract_text`

### Orchestration / DAG
- `POST /api/plan`
- `POST /api/execute_dag`
- `GET /api/dag/{task_id}`
- `WS /ws/dag` (real-time DAG state updates)

### MCP
- `GET /api/mcp/tools`
- `POST /api/mcp/execute`
- `POST /api/mcp/rpc`

---

## Project Structure

```text
prometheus/
├── backend/
│   ├── orchestration/
│   │   ├── dag_engine.py
│   │   ├── swarm_coordinator.py
│   │   └── planner.py
│   ├── routing/
│   │   └── model_router.py
│   ├── mcp/
│   │   ├── mcp_client.py
│   │   ├── mcp_server.py
│   │   └── mcp_protocol.py
│   ├── tools/
│   │   ├── git_tool.py
│   │   ├── browser_tool.py
│   │   ├── email_tool.py
│   │   ├── calendar_tool.py
│   │   ├── utility_tools.py
│   │   └── ...existing tools
│   ├── agent.py
│   ├── main.py
│   └── requirements.txt
├── frontend/src/components/
│   ├── DAGVisualizer.svelte
│   ├── PlanPanel.svelte
│   ├── TaskMonitor.svelte
│   └── ...existing components
└── install.sh
```

---

## Install

```bash
git clone https://github.com/TRADER8666/prometheus.git
cd prometheus
chmod +x install.sh
./install.sh
```

Installer includes:
- Docker + Compose
- host-native Ollama + model pulls (`llama3.2:3b`, `qwen2.5-coder:1.5b`, `nomic-embed-text`, `llava`)
- Python AI/tool dependencies
- Playwright Chromium install (`playwright install chromium`)
- YOLO weight caching
- service + LAN setup

---

## Frontend UX

Tabs in UI:
- Chat
- Vision / Images
- **Orchestration** (plan generation, DAG visualization, task monitoring)

DAG colors:
- pending: gray
- in_progress: blue
- completed: green
- failed: red

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

## Notes

- Heavy models may require high VRAM; CPU fallback is supported but slower.
- Playwright/browser and diffusion features require additional runtime packages and memory.
- Add authentication/TLS before exposing beyond LAN.
