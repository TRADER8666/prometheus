import json
from typing import Any, Dict, List, Optional

from database import db_cursor, now_iso


class BookmarksService:
    def create_bookmark(self, url: str, title: str = "", description: str = "", tags: Optional[List[str]] = None, folder: str = "", favicon: str = "") -> Dict[str, Any]:
        tags = tags or []
        ts = now_iso()
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO bookmarks(url, title, description, tags, folder, favicon, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (url, title, description, json.dumps(tags), folder, favicon, ts, ts),
            )
            bid = cur.lastrowid
            cur.execute("SELECT * FROM bookmarks WHERE id=?", (bid,))
            row = dict(cur.fetchone())
        row["tags"] = json.loads(row.get("tags") or "[]")
        return row

    def list_bookmarks(self, query: str = "", tag: str = "", folder: str = "") -> List[Dict[str, Any]]:
        with db_cursor() as cur:
            if query:
                cur.execute(
                    """
                    SELECT b.* FROM bookmarks b
                    JOIN bookmarks_fts f ON f.rowid = b.id
                    WHERE bookmarks_fts MATCH ?
                    ORDER BY b.updated_at DESC
                    """,
                    (query,),
                )
            else:
                cur.execute("SELECT * FROM bookmarks ORDER BY updated_at DESC")
            rows = [dict(x) for x in cur.fetchall()]

        out = []
        for r in rows:
            r["tags"] = json.loads(r.get("tags") or "[]")
            if tag and tag not in r["tags"]:
                continue
            if folder and r.get("folder") != folder:
                continue
            out.append(r)
        return out

    def get_bookmark(self, bookmark_id: int) -> Optional[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM bookmarks WHERE id=?", (bookmark_id,))
            row = cur.fetchone()
        if not row:
            return None
        out = dict(row)
        out["tags"] = json.loads(out.get("tags") or "[]")
        return out

    def update_bookmark(self, bookmark_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_bookmark(bookmark_id)
        if not existing:
            return None

        payload = {
            "url": data.get("url", existing["url"]),
            "title": data.get("title", existing.get("title", "")),
            "description": data.get("description", existing.get("description", "")),
            "tags": data.get("tags", existing.get("tags", [])),
            "folder": data.get("folder", existing.get("folder", "")),
            "favicon": data.get("favicon", existing.get("favicon", "")),
        }
        if not isinstance(payload["tags"], list):
            payload["tags"] = existing.get("tags", [])

        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE bookmarks SET url=?, title=?, description=?, tags=?, folder=?, favicon=?, updated_at=? WHERE id=?",
                (
                    payload["url"],
                    payload["title"],
                    payload["description"],
                    json.dumps(payload["tags"]),
                    payload["folder"],
                    payload["favicon"],
                    now_iso(),
                    bookmark_id,
                ),
            )
        return self.get_bookmark(bookmark_id)

    def delete_bookmark(self, bookmark_id: int) -> bool:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM bookmarks WHERE id=?", (bookmark_id,))
            return cur.rowcount > 0

    def export_bookmarks(self) -> Dict[str, Any]:
        return {"bookmarks": self.list_bookmarks()}

    def import_bookmarks(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        items = payload.get("bookmarks", [])
        created = 0
        for b in items:
            try:
                self.create_bookmark(
                    url=b.get("url", ""),
                    title=b.get("title", ""),
                    description=b.get("description", ""),
                    tags=b.get("tags", []),
                    folder=b.get("folder", ""),
                    favicon=b.get("favicon", ""),
                )
                created += 1
            except Exception:
                continue
        return {"ok": True, "imported": created}
