# Prometheus AI Workspace

Prometheus is a locally-hostable AI workspace with chat + agent tools + vision.

## Features

- Local LLM chat via **Ollama**
- RAG / memory via **ChromaDB**
- Agent tool loop for code/file/search/rag
- **Vision tools**:
  - YOLO object detection (`ultralytics`)
  - Stable Diffusion text-to-image (`diffusers`)
  - Stable Diffusion inpainting
  - Ollama vision analysis (`llava` / `bakllava`)
  - OCR via `easyocr`
- Svelte UI with chat + dedicated vision panel

## Architecture

- Frontend (Svelte/Vite): `3000`
- Backend (FastAPI): `8000`
- Ollama (host native): `11434`
- ChromaDB: `8001`
- SearXNG: `8080`
- Nginx reverse proxy: `80`

Nginx routes:
- `/` -> frontend
- `/api/*` -> backend

## Vision API Endpoints

- `POST /api/upload_image` - upload image
- `GET /api/images/{filename}` - serve uploaded/generated image
- `POST /api/detect_objects` - YOLO detection
- `POST /api/generate_image` - text-to-image
- `POST /api/edit_image` - inpainting
- `POST /api/analyze_image` - Ollama vision analysis
- `POST /api/extract_text` - OCR

(Backend also exposes non-prefixed aliases for direct local dev.)

## Tool Call Syntax (chat)

```text
[[tool:detect_objects {"image_path":"/tmp/prometheus-images/sample.png"}]]
[[tool:generate_image {"prompt":"cyberpunk city at night"}]]
[[tool:edit_image {"image_path":"...","mask_path":"...","prompt":"add a tree"}]]
[[tool:analyze_image {"image_path":"...","prompt":"what is in this image?"}]]
[[tool:extract_text {"image_path":"..."}]]
```

## Installation

```bash
git clone https://github.com/TRADER8666/prometheus.git
cd prometheus
chmod +x install.sh
./install.sh
```

`install.sh` now also:
- installs Python AI dependencies (`torch`, `diffusers`, `ultralytics`, `easyocr`, etc.)
- detects CPU/GPU and attempts suitable PyTorch install
- caches YOLO model weights (`yolov8n.pt`)
- pulls Ollama vision model (`llava`)
- creates `backend/workspace/images`

## Local Development

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

## Notes

- CPU fallback is supported for all vision features (slower).
- Diffusion and YOLO models are lazily loaded/cached to avoid repeated downloads.
- For production internet exposure, add auth + TLS + security hardening.
