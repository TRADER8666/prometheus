from typing import Dict, Any
import httpx
import os

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = payload.get("query", "")
    if not query.strip():
        return {"ok": False, "error": "query required"}

    url = f"{SEARXNG_URL}/search"
    params = {"q": query, "format": "json"}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        results = [
            {
                "title": x.get("title"),
                "url": x.get("url"),
                "content": x.get("content", ""),
            }
            for x in data.get("results", [])[:5]
        ]
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}
