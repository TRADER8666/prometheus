import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from database import db_cursor, now_iso


class NotesService:
    def create_note(self, title: str, content: str = "", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        tags = tags or []
        ts = now_iso()
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO notes(title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (title, content, json.dumps(tags), ts, ts),
            )
            note_id = cur.lastrowid
            cur.execute("SELECT * FROM notes WHERE id=?", (note_id,))
            row = dict(cur.fetchone())
        row["tags"] = json.loads(row.get("tags") or "[]")
        return row

    def list_notes(self, query: str = "", tag: str = "") -> List[Dict[str, Any]]:
        with db_cursor() as cur:
            if query:
                cur.execute(
                    """
                    SELECT n.* FROM notes n
                    JOIN notes_fts f ON f.rowid = n.id
                    WHERE notes_fts MATCH ?
                    ORDER BY n.updated_at DESC
                    """,
                    (query,),
                )
            else:
                cur.execute("SELECT * FROM notes ORDER BY updated_at DESC")
            rows = [dict(x) for x in cur.fetchall()]

        out = []
        for r in rows:
            r["tags"] = json.loads(r.get("tags") or "[]")
            if tag and tag not in r["tags"]:
                continue
            out.append(r)
        return out

    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM notes WHERE id=?", (note_id,))
            row = cur.fetchone()
        if not row:
            return None
        out = dict(row)
        out["tags"] = json.loads(out.get("tags") or "[]")
        return out

    def update_note(self, note_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_note(note_id)
        if not existing:
            return None

        title = data.get("title", existing["title"])
        content = data.get("content", existing["content"])
        tags = data.get("tags", existing["tags"])
        if not isinstance(tags, list):
            tags = existing["tags"]

        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE notes SET title=?, content=?, tags=?, updated_at=? WHERE id=?",
                (title, content, json.dumps(tags), now_iso(), note_id),
            )
        return self.get_note(note_id)

    def delete_note(self, note_id: int) -> bool:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM notes WHERE id=?", (note_id,))
            return cur.rowcount > 0

    def export_note_markdown(self, note_id: int, export_dir: str = "/tmp/prometheus-note-exports") -> Optional[str]:
        note = self.get_note(note_id)
        if not note:
            return None
        p = Path(export_dir)
        p.mkdir(parents=True, exist_ok=True)
        filename = f"note_{note_id}_{note['title'].strip().replace(' ', '_')[:40]}.md"
        target = p / filename
        md = f"# {note['title']}\n\n{note['content']}\n\n---\nTags: {', '.join(note['tags'])}\n"
        target.write_text(md, encoding="utf-8")
        return str(target)
