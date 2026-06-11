import json
from typing import Any, Dict, List, Optional

from database import db_cursor, now_iso


class KanbanService:
    # Boards
    def create_board(self, name: str, description: str = "") -> Dict[str, Any]:
        ts = now_iso()
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM kanban_boards")
            pos = int(cur.fetchone()[0] or 1)
            cur.execute(
                "INSERT INTO kanban_boards(name, description, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name, description, pos, ts, ts),
            )
            bid = cur.lastrowid
            cur.execute("SELECT * FROM kanban_boards WHERE id=?", (bid,))
            return dict(cur.fetchone())

    def list_boards(self) -> List[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM kanban_boards ORDER BY position ASC, id ASC")
            return [dict(x) for x in cur.fetchall()]

    def get_board(self, board_id: int) -> Optional[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM kanban_boards WHERE id=?", (board_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def update_board(self, board_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        board = self.get_board(board_id)
        if not board:
            return None
        name = data.get("name", board["name"])
        desc = data.get("description", board.get("description", ""))
        pos = int(data.get("position", board.get("position", 1)))
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE kanban_boards SET name=?, description=?, position=?, updated_at=? WHERE id=?",
                (name, desc, pos, now_iso(), board_id),
            )
        return self.get_board(board_id)

    def delete_board(self, board_id: int) -> bool:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM kanban_boards WHERE id=?", (board_id,))
            return cur.rowcount > 0

    # Columns
    def create_column(self, board_id: int, name: str) -> Dict[str, Any]:
        ts = now_iso()
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM kanban_columns WHERE board_id=?", (board_id,))
            pos = int(cur.fetchone()[0] or 1)
            cur.execute(
                "INSERT INTO kanban_columns(board_id, name, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (board_id, name, pos, ts, ts),
            )
            cid = cur.lastrowid
            cur.execute("SELECT * FROM kanban_columns WHERE id=?", (cid,))
            return dict(cur.fetchone())

    def list_columns(self, board_id: int) -> List[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM kanban_columns WHERE board_id=? ORDER BY position ASC, id ASC", (board_id,))
            return [dict(x) for x in cur.fetchall()]

    def update_column(self, column_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM kanban_columns WHERE id=?", (column_id,))
            row = cur.fetchone()
        if not row:
            return None
        col = dict(row)
        name = data.get("name", col["name"])
        pos = int(data.get("position", col.get("position", 1)))
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE kanban_columns SET name=?, position=?, updated_at=? WHERE id=?", (name, pos, now_iso(), column_id))
            cur.execute("SELECT * FROM kanban_columns WHERE id=?", (column_id,))
            return dict(cur.fetchone())

    def delete_column(self, column_id: int) -> bool:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM kanban_columns WHERE id=?", (column_id,))
            return cur.rowcount > 0

    # Cards
    def create_card(self, column_id: int, title: str, description: str = "", assignee: str = "", due_date: str = "", labels=None, checklist=None) -> Dict[str, Any]:
        labels = labels or []
        checklist = checklist or []
        ts = now_iso()
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM kanban_cards WHERE column_id=?", (column_id,))
            pos = int(cur.fetchone()[0] or 1)
            cur.execute(
                """
                INSERT INTO kanban_cards(column_id, title, description, assignee, due_date, labels, checklist, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (column_id, title, description, assignee, due_date, json.dumps(labels), json.dumps(checklist), pos, ts, ts),
            )
            cid = cur.lastrowid
            cur.execute("SELECT * FROM kanban_cards WHERE id=?", (cid,))
            card = dict(cur.fetchone())
        card["labels"] = json.loads(card.get("labels") or "[]")
        card["checklist"] = json.loads(card.get("checklist") or "[]")
        return card

    def list_cards(self, column_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with db_cursor() as cur:
            if column_id is None:
                cur.execute("SELECT * FROM kanban_cards ORDER BY column_id ASC, position ASC, id ASC")
            else:
                cur.execute("SELECT * FROM kanban_cards WHERE column_id=? ORDER BY position ASC, id ASC", (column_id,))
            rows = [dict(x) for x in cur.fetchall()]
        for r in rows:
            r["labels"] = json.loads(r.get("labels") or "[]")
            r["checklist"] = json.loads(r.get("checklist") or "[]")
        return rows

    def get_card(self, card_id: int) -> Optional[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM kanban_cards WHERE id=?", (card_id,))
            row = cur.fetchone()
        if not row:
            return None
        c = dict(row)
        c["labels"] = json.loads(c.get("labels") or "[]")
        c["checklist"] = json.loads(c.get("checklist") or "[]")
        return c

    def update_card(self, card_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        card = self.get_card(card_id)
        if not card:
            return None
        payload = {
            "column_id": int(data.get("column_id", card["column_id"])),
            "title": data.get("title", card["title"]),
            "description": data.get("description", card.get("description", "")),
            "assignee": data.get("assignee", card.get("assignee", "")),
            "due_date": data.get("due_date", card.get("due_date", "")),
            "labels": data.get("labels", card.get("labels", [])),
            "checklist": data.get("checklist", card.get("checklist", [])),
            "position": int(data.get("position", card.get("position", 1))),
        }
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE kanban_cards
                SET column_id=?, title=?, description=?, assignee=?, due_date=?, labels=?, checklist=?, position=?, updated_at=?
                WHERE id=?
                """,
                (
                    payload["column_id"],
                    payload["title"],
                    payload["description"],
                    payload["assignee"],
                    payload["due_date"],
                    json.dumps(payload["labels"]),
                    json.dumps(payload["checklist"]),
                    payload["position"],
                    now_iso(),
                    card_id,
                ),
            )
        return self.get_card(card_id)

    def delete_card(self, card_id: int) -> bool:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM kanban_cards WHERE id=?", (card_id,))
            return cur.rowcount > 0

    def move_card(self, card_id: int, target_column_id: int, position: int) -> Optional[Dict[str, Any]]:
        card = self.get_card(card_id)
        if not card:
            return None

        with db_cursor(commit=True) as cur:
            # make room at target position
            cur.execute(
                "UPDATE kanban_cards SET position = position + 1, updated_at=? WHERE column_id=? AND position>=? AND id!=?",
                (now_iso(), target_column_id, position, card_id),
            )
            cur.execute(
                "UPDATE kanban_cards SET column_id=?, position=?, updated_at=? WHERE id=?",
                (target_column_id, position, now_iso(), card_id),
            )

        return self.get_card(card_id)
