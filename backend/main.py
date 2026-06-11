import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from agent import TOOL_MAP, get_default_agent
from database import db_cursor, init_db, now_iso
from mcp.mcp_server import MCPServer
from models import (
    ChatRequest,
    ChatResponse,
    ConversationOut,
    ExecuteDAGRequest,
    ImageEditRequest,
    ImageGenerateRequest,
    ImageUploadResponse,
    MCPExecuteRequest,
    MessageOut,
    ModelPullRequest,
    ModelRecommendRequest,
    OCRRequest,
    ObjectDetectRequest,
    PlanRequest,
    RecommendationOut,
    VisionAnalyzeRequest,
)
from orchestration.dag_engine import DAGNode
from routing.model_router import ModelRouter
from tools import image_editing, image_generation, object_detection, ocr, rag, vision_analysis
from cookbook import detect_hardware, recommend_models

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "/tmp/prometheus-images")).resolve()
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Prometheus API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = get_default_agent(OLLAMA_URL)
model_router = ModelRouter()

DAG_STATES: Dict[str, Dict[str, Any]] = {}
DAG_TASKS: Dict[str, asyncio.Task] = {}


class WebSocketHub:
    def __init__(self):
        self.clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, event: Dict[str, Any]):
        dead: List[WebSocket] = []
        for ws in self.clients:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.disconnect(d)


ws_hub = WebSocketHub()


mcp_server = MCPServer()
for tool_name, fn in TOOL_MAP.items():
    mcp_server.register_tool(
        name=tool_name,
        schema={"type": "object", "properties": {}},
        handler=fn,
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

    image_context = ""
    if req.image_paths:
        analysis = vision_analysis.analyze(
            image_path=req.image_paths[0],
            prompt=f"Analyze this image for user task: {req.message}",
            model=req.vision_model or "llava",
        )
        if analysis.get("ok"):
            image_context = f"\n\nImage context:\n{analysis.get('response', '')[:2500]}"

    tool_results = []
    if req.use_tools:
        tool_results = agent.execute_tools(req.message, req.image_paths)
        for tr in tool_results:
            _log_tool_call(conversation_id, tr.get("tool", "unknown"), tr.get("input", {}), tr.get("output", {}))

    model = req.model or model_router.route_task(req.message)
    tool_context = "\n\nTool outputs:\n" + json.dumps(tool_results, ensure_ascii=False)[:5000] if tool_results else ""

    prompt = f"""You are Prometheus, a local AI workspace assistant.
User said:
{req.message}
{context}
{image_context}
{tool_context}
Answer clearly and concisely."""

    try:
        answer = await _ollama_generate(model, prompt)
    except Exception as e:
        answer = f"Model call failed: {e}"

    _add_message(conversation_id, "assistant", answer, model)
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

    return ImageUploadResponse(ok=True, filename=ts_name, image_path=str(dst), image_url=f"/api/images/{ts_name}")


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


# --------------------------
# Orchestration APIs
# --------------------------


@app.post("/api/plan")
async def plan_task(req: PlanRequest):
    plan = await agent.create_plan(req.request)
    return {"ok": True, "plan": plan}


@app.get("/api/dag/{task_id}")
def get_dag_state(task_id: str):
    if task_id not in DAG_STATES:
        raise HTTPException(status_code=404, detail="task not found")
    return DAG_STATES[task_id]


@app.post("/api/execute_dag")
async def execute_dag(req: ExecuteDAGRequest):
    request = req.request or ""

    if req.plan:
        nodes = [
            DAGNode(
                id=str(x.get("id", f"node_{i+1}")),
                task={"action": x.get("action", "noop"), "input": x.get("input", {})},
                dependencies=x.get("dependencies", []),
                condition=x.get("condition"),
            )
            for i, x in enumerate(req.plan)
        ]
    else:
        nodes = await agent.create_dag(request)

    async def on_state_change_async(task_id: str, state: Dict[str, Any]):
        DAG_STATES[task_id] = state
        await ws_hub.broadcast({"type": "dag_update", "task_id": task_id, "state": state})

    def on_state_change(task_id: str, state: Dict[str, Any]):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(on_state_change_async(task_id, state))
        except RuntimeError:
            pass

    async def _runner():
        result = await agent.execute_dag(
            request=request,
            nodes=nodes,
            max_parallel=req.max_parallel,
            on_state_change=on_state_change,
        )
        DAG_STATES[result["dag"]["task_id"]] = result
        await ws_hub.broadcast({"type": "dag_completed", "task_id": result["dag"]["task_id"], "state": result})
        return result

    task = asyncio.create_task(_runner())
    DAG_TASKS[str(id(task))] = task
    result = await task
    return {"ok": True, "task_id": result["dag"]["task_id"], "result": result}


@app.post("/api/models/recommend")
async def recommend_model(req: ModelRecommendRequest):
    return {"ok": True, "recommendation": model_router.recommend(req.task, req.available_models)}


# --------------------------
# MCP APIs
# --------------------------


@app.get("/mcp/tools")
@app.get("/api/mcp/tools")
def list_mcp_tools():
    return {"ok": True, "tools": mcp_server.list_tools()}


@app.post("/mcp/execute")
@app.post("/api/mcp/execute")
def execute_mcp_tool(req: MCPExecuteRequest):
    try:
        out = mcp_server.call_tool(req.tool, req.arguments)
        return {"ok": True, "output": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/mcp/rpc")
@app.post("/api/mcp/rpc")
def mcp_rpc(payload: Dict[str, Any]):
    return mcp_server.handle_rpc(payload)


@app.websocket("/ws/dag")
async def ws_dag(websocket: WebSocket):
    await ws_hub.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "message": "dag websocket connected"})
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)
    except Exception:
        ws_hub.disconnect(websocket)
