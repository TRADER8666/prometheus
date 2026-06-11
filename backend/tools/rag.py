import os
from typing import Dict, Any, List

import chromadb

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION = os.getenv("CHROMA_COLLECTION", "prometheus_docs")

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        _collection = _client.get_or_create_collection(name=COLLECTION)
    return _collection


def _chunks(text: str, size: int = 700, overlap: int = 100) -> List[str]:
    out = []
    i = 0
    while i < len(text):
        out.append(text[i : i + size])
        i += max(1, size - overlap)
    return out


def add_document(doc_id_prefix: str, text: str, metadata: Dict[str, Any] | None = None):
    metadata = metadata or {}
    parts = _chunks(text)
    ids = [f"{doc_id_prefix}-{idx}" for idx in range(len(parts))]
    metas = [{**metadata, "chunk": idx} for idx in range(len(parts))]
    _get_collection().add(ids=ids, documents=parts, metadatas=metas)
    return ids, parts


def query(text: str, n_results: int = 3):
    res = _get_collection().query(query_texts=[text], n_results=n_results)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    return list(zip(docs, metas))


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = payload.get("action")
    if action == "add":
        ids, _ = add_document(
            payload.get("id_prefix", "doc"),
            payload.get("text", ""),
            payload.get("metadata", {}),
        )
        return {"ok": True, "ids": ids}
    if action == "query":
        hits = query(payload.get("text", ""), payload.get("n_results", 3))
        return {"ok": True, "hits": [{"content": d, "metadata": m} for d, m in hits]}
    return {"ok": False, "error": "Unknown rag action"}
