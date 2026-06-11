import json
import os
import shutil
import time
from pathlib import Path
from typing import List

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from database import db_cursor, init_db, now_iso
from models import (
    ChatRequest,
    ChatResponse,
    ConversationOut,
    MessageOut,
    ModelPullRequest,
    RecommendationOut,
    ImageUploadResponse,
    ObjectDetectRequest,
    ImageGenerateRequest,
    ImageEditRequest,
    VisionAnalyzeRequest,
    OCRRequest,
)
from cookbook import detect_hardware, recommend_models
from agent import execute_tools
from tools import rag, object_detection, image_generation, image_editing, vision_analysis, ocr

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "/tmp/prometheus-images")).resolve()
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Prometheus API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


def _create_conversation(title: str) -> int:
    now = now_iso()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO conversations(title, created_at, updated_at) VALUES (?, ?, ?)",
            (title[:120], now, now),
        )
        return cur.lastrowid


def _add_message(conversation_id: int, role: str, content: str, model: str | None = None) -> int:
    now = now_iso()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO messages(conversation_id, role, content, model, created_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, role, content, model, now),
        )
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
        return cur.lastrowid


def _log_tool_call(conversation_id: int | None, tool: str, tool_input: dict, tool_output: dict):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO tool_calls(conversation_id, tool_name, tool_input, tool_output, created_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, tool, json.dumps(tool_input), json.dumps(tool_output), now_iso()),
        )


async def _ollama_generate(model: str, prompt: str) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        r.raise_for_status()
        return r.json().get("response", "")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or _create_conversation(req.message[:60] or "New conversation")
    _add_message(conversation_id, "user", req.message, req.model)

    context = ""
    if req.use_rag:
        hits = rag.query(req.message, 3)
        if hits:
            context = "\n\nRelevant memory:\n" + "\n---\n".join([h[0] for h in hits])

    # If an image is attached, optionally enrich prompt using vision model.
    image_context = ""
    if req.image_paths:
        first_image = req.image_paths[0]
        analysis = vision_analysis.analyze(
            image_path=first_image,
            prompt=f"Analyze the image for this user question: {req.message}",
            model=req.vision_model or "llava",
        )
        if analysis.get("ok"):
            image_context = f"\n\nImage context from {first_image}:\n{analysis.get('response', '')[:2000]}"

    tool_results = []
    if req.use_tools:
        tool_results = execute_tools(req.message, req.image_paths)
        for tr in tool_results:
            _log_tool_call(conversation_id, tr.get("tool", "unknown"), tr.get("input", {}), tr.get("output", {}))

    tool_context = ""
    if tool_results:
        tool_context = "\n\nTool outputs:\n" + json.dumps(tool_results, ensure_ascii=False)[:5000]

    prompt = f"""You are Prometheus, a local AI workspace assistant.
User said:
{req.message}
{context}
{image_context}
{tool_context}
Answer clearly and concisely."""

    try:
        answer = await _ollama_generate(req.model, prompt)
    except Exception as e:
        answer = f"Model call failed: {e}"

    _add_message(conversation_id, "assistant", answer, req.model)
    return ChatResponse(conversation_id=conversation_id, assistant_message=answer)


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    resp = await chat(req)

    async def gen():
        text = resp.assistant_message
        for i in range(0, len(text), 30):
            chunk = text[i : i + 30]
            yield f"data: {json.dumps({'delta': chunk, 'conversation_id': resp.conversation_id})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/conversations", response_model=List[ConversationOut])
def list_conversations():
    with db_cursor() as cur:
        cur.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
        rows = [dict(x) for x in cur.fetchall()]
    return rows


@app.post("/conversations", response_model=ConversationOut)
def create_conversation(title: str = "New conversation"):
    cid = _create_conversation(title)
    with db_cursor() as cur:
        cur.execute("SELECT * FROM conversations WHERE id=?", (cid,))
        row = cur.fetchone()
    return dict(row)


@app.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
def get_messages(conversation_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id ASC", (conversation_id,))
        rows = [dict(x) for x in cur.fetchall()]
    return rows


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
    return {"ok": True}


@app.get("/models")
async def list_models():
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{OLLAMA_URL}/api/tags")
        r.raise_for_status()
    return r.json()


@app.post("/models/pull")
async def pull_model(req: ModelPullRequest):
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{OLLAMA_URL}/api/pull", json={"name": req.model, "stream": False})
        r.raise_for_status()
    return r.json()


@app.delete("/models/{model_name}")
async def delete_model(model_name: str):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.delete(f"{OLLAMA_URL}/api/delete", json={"name": model_name})
        if r.status_code >= 400:
            raise HTTPException(r.status_code, r.text)
    return {"ok": True}


@app.get("/cookbook/recommendations", response_model=RecommendationOut)
def recommendations():
    hw = detect_hardware()
    rec = recommend_models(hw)
    return RecommendationOut(hardware=hw, recommendations=rec)


@app.post("/documents/upload")
@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    data = await file.read()
    text = data.decode("utf-8", errors="ignore")
    ids, chunks = rag.add_document(file.filename, text, {"filename": file.filename})

    with db_cursor(commit=True) as cur:
        for cid, chunk_text in zip(ids, chunks):
            cur.execute(
                "INSERT INTO documents(filename, chunk_id, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (file.filename, cid, chunk_text, json.dumps({"filename": file.filename}), now_iso()),
            )
    return {"ok": True, "chunks": len(ids)}


# --------------------------
# Vision / Image Endpoints
# --------------------------

@app.post("/upload_image", response_model=ImageUploadResponse)
@app.post("/api/upload_image", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    ts_name = f"{int(time.time() * 1000)}_{Path(file.filename).name}"
    dst = IMAGE_DIR / ts_name
    with dst.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    return ImageUploadResponse(
        ok=True,
        filename=ts_name,
        image_path=str(dst),
        image_url=f"/api/images/{ts_name}",
    )


@app.get("/images/{filename}")
@app.get("/api/images/{filename}")
def serve_image(filename: str):
    p = (IMAGE_DIR / filename).resolve()
    if not str(p).startswith(str(IMAGE_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not p.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(p))


@app.post("/detect_objects")
@app.post("/api/detect_objects")
def detect_objects(req: ObjectDetectRequest):
    out = object_detection.execute(req.model_dump())
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=out.get("error", "object detection failed"))
    return out


@app.post("/generate_image")
@app.post("/api/generate_image")
def generate_image(req: ImageGenerateRequest):
    out = image_generation.execute(req.model_dump())
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=out.get("error", "image generation failed"))
    if out.get("filename"):
        out["image_url"] = f"/api/images/{out['filename']}"
    return out


@app.post("/edit_image")
@app.post("/api/edit_image")
def edit_image(req: ImageEditRequest):
    out = image_editing.execute(req.model_dump())
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=out.get("error", "image editing failed"))
    if out.get("filename"):
        out["image_url"] = f"/api/images/{out['filename']}"
    return out


@app.post("/analyze_image")
@app.post("/api/analyze_image")
def analyze_image(req: VisionAnalyzeRequest):
    out = vision_analysis.execute(req.model_dump())
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=out.get("error", "vision analysis failed"))
    return out


@app.post("/extract_text")
@app.post("/api/extract_text")
def extract_text(req: OCRRequest):
    out = ocr.execute(req.model_dump())
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=out.get("error", "ocr failed"))
    return out
