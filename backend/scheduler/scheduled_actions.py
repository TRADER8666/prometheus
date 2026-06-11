import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict

from database import db_cursor, now_iso


def action_email_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Placeholder local summary; real SMTP can be invoked through email tool if desired.
    summary = payload.get("summary", "Daily summary from Prometheus")
    recipient = payload.get("recipient", "local-user")
    return {"ok": True, "recipient": recipient, "summary": summary, "sent": False, "mode": "placeholder"}


def action_daily_briefing(payload: Dict[str, Any]) -> Dict[str, Any]:
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM notes")
        notes_count = int(cur.fetchone()[0] or 0)
        cur.execute("SELECT COUNT(*) FROM bookmarks")
        bookmarks_count = int(cur.fetchone()[0] or 0)
        cur.execute("SELECT COUNT(*) FROM kanban_cards")
        cards_count = int(cur.fetchone()[0] or 0)
    return {
        "ok": True,
        "generated_at": now_iso(),
        "briefing": {
            "notes_count": notes_count,
            "bookmarks_count": bookmarks_count,
            "kanban_cards_count": cards_count,
            "message": "Daily briefing generated.",
        },
    }


def action_backup_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    src_dir = Path(payload.get("src_dir", "/home/ubuntu/prometheus/backend"))
    dst_zip = Path(payload.get("dst_zip", "/tmp/prometheus_backup.zip"))
    dst_zip.parent.mkdir(parents=True, exist_ok=True)
    base_name = str(dst_zip.with_suffix(""))
    archive = shutil.make_archive(base_name, "zip", root_dir=str(src_dir))
    return {"ok": True, "backup": archive}


def action_system_health(payload: Dict[str, Any]) -> Dict[str, Any]:
    import psutil

    vm = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    return {
        "ok": True,
        "health": {
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "memory_percent": vm.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
        },
    }


def action_custom_agent_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    # This action is intentionally generic and can be interpreted by higher-level orchestrators.
    return {"ok": True, "task": payload.get("task", ""), "status": "accepted"}


def register_default_actions(scheduler) -> None:
    actions: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
        "email_summary": action_email_summary,
        "daily_briefing": action_daily_briefing,
        "backup_data": action_backup_data,
        "system_health": action_system_health,
        "custom_agent_task": action_custom_agent_task,
    }
    for name, fn in actions.items():
        scheduler.register_action(name, fn)
