import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "/data/prometheus.db")


def _ensure_db_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection():
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def db_cursor(commit: bool = False):
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    finally:
        cur.close()
        conn.close()


def _init_core_tables(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            tool_name TEXT NOT NULL,
            tool_input TEXT,
            tool_output TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
        )
        """
    )


def _init_notes_tables(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(title, content, tags)")
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
          INSERT INTO notes_fts(rowid, title, content, tags) VALUES (new.id, new.title, new.content, COALESCE(new.tags, ''));
        END;
        """
    )
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
          INSERT INTO notes_fts(notes_fts, rowid, title, content, tags) VALUES('delete', old.id, old.title, old.content, COALESCE(old.tags, ''));
        END;
        """
    )
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
          INSERT INTO notes_fts(notes_fts, rowid, title, content, tags) VALUES('delete', old.id, old.title, old.content, COALESCE(old.tags, ''));
          INSERT INTO notes_fts(rowid, title, content, tags) VALUES (new.id, new.title, new.content, COALESCE(new.tags, ''));
        END;
        """
    )


def _init_kanban_tables(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kanban_boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            position INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kanban_columns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(board_id) REFERENCES kanban_boards(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kanban_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            column_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            assignee TEXT,
            due_date TEXT,
            labels TEXT,
            checklist TEXT,
            position INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(column_id) REFERENCES kanban_columns(id) ON DELETE CASCADE
        )
        """
    )


def _init_bookmark_tables(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT,
            description TEXT,
            tags TEXT,
            folder TEXT,
            favicon TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks_fts USING fts5(url, title, description, tags, folder)")
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS bookmarks_ai AFTER INSERT ON bookmarks BEGIN
          INSERT INTO bookmarks_fts(rowid, url, title, description, tags, folder)
          VALUES (new.id, new.url, COALESCE(new.title,''), COALESCE(new.description,''), COALESCE(new.tags,''), COALESCE(new.folder,''));
        END;
        """
    )
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS bookmarks_ad AFTER DELETE ON bookmarks BEGIN
          INSERT INTO bookmarks_fts(bookmarks_fts, rowid, url, title, description, tags, folder)
          VALUES('delete', old.id, old.url, COALESCE(old.title,''), COALESCE(old.description,''), COALESCE(old.tags,''), COALESCE(old.folder,''));
        END;
        """
    )
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS bookmarks_au AFTER UPDATE ON bookmarks BEGIN
          INSERT INTO bookmarks_fts(bookmarks_fts, rowid, url, title, description, tags, folder)
          VALUES('delete', old.id, old.url, COALESCE(old.title,''), COALESCE(old.description,''), COALESCE(old.tags,''), COALESCE(old.folder,''));
          INSERT INTO bookmarks_fts(rowid, url, title, description, tags, folder)
          VALUES (new.id, new.url, COALESCE(new.title,''), COALESCE(new.description,''), COALESCE(new.tags,''), COALESCE(new.folder,''));
        END;
        """
    )


def _init_scheduler_tables(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            schedule TEXT NOT NULL,
            action TEXT NOT NULL,
            action_payload TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduler_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            run_at TEXT NOT NULL,
            status TEXT NOT NULL,
            output TEXT,
            error TEXT,
            FOREIGN KEY(job_id) REFERENCES scheduled_jobs(id) ON DELETE SET NULL
        )
        """
    )


def init_db():
    with db_cursor(commit=True) as cur:
        _init_core_tables(cur)
        _init_notes_tables(cur)
        _init_kanban_tables(cur)
        _init_bookmark_tables(cur)
        _init_scheduler_tables(cur)


def now_iso() -> str:
    return datetime.utcnow().isoformat()
