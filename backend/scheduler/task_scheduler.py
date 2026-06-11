import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter

from database import db_cursor, now_iso


@dataclass
class CronJob:
    id: int
    name: str
    schedule: str
    action: str
    enabled: bool
    last_run: Optional[str]
    next_run: Optional[str]


class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.actions: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.started = False

    def start(self):
        if not self.started:
            self.scheduler.start()
            self.started = True
            self._load_enabled_jobs_from_db()

    def shutdown(self):
        if self.started:
            self.scheduler.shutdown(wait=False)
            self.started = False

    def register_action(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self.actions[name] = fn

    def parse_natural_language(self, text: str) -> str:
        t = (text or "").strip().lower()
        mapping = {
            "every minute": "* * * * *",
            "every hour": "0 * * * *",
            "every day": "0 9 * * *",
            "daily": "0 9 * * *",
            "every morning at 8 am": "0 8 * * *",
            "every morning": "0 8 * * *",
            "every evening": "0 18 * * *",
            "every monday": "0 9 * * 1",
            "weekly": "0 9 * * 1",
        }
        return mapping.get(t, text)

    def validate_cron(self, pattern: str) -> bool:
        try:
            croniter(pattern, datetime.utcnow())
            return True
        except Exception:
            return False

    def _next_run(self, pattern: str) -> str:
        itr = croniter(pattern, datetime.utcnow())
        return itr.get_next(datetime).isoformat()

    def _parse_cron_for_aps(self, pattern: str) -> Dict[str, Any]:
        minute, hour, day, month, day_of_week = pattern.split()
        return {
            "minute": minute,
            "hour": hour,
            "day": day,
            "month": month,
            "day_of_week": day_of_week,
        }

    def _record_history(self, job_id: int, status: str, output: Dict[str, Any] | None = None, error: str = ""):
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO scheduler_history(job_id, run_at, status, output, error) VALUES (?, ?, ?, ?, ?)",
                (job_id, now_iso(), status, json.dumps(output or {}), error),
            )

    def _execute(self, job_id: int, action: str, payload: Dict[str, Any]):
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE scheduled_jobs SET last_run=?, updated_at=? WHERE id=?", (now_iso(), now_iso(), job_id))

        fn = self.actions.get(action)
        if not fn:
            self._record_history(job_id, "failed", error=f"Unknown action: {action}")
            return

        try:
            result = fn(payload)
            self._record_history(job_id, "success", output=result)
        except Exception as e:
            self._record_history(job_id, "failed", error=str(e))

    def _schedule_aps_job(self, job_id: int, pattern: str, action: str, payload: Dict[str, Any]):
        trigger = CronTrigger(**self._parse_cron_for_aps(pattern), timezone="UTC")
        self.scheduler.add_job(
            func=self._execute,
            trigger=trigger,
            args=[job_id, action, payload],
            id=f"scheduled-job-{job_id}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    def _load_enabled_jobs_from_db(self):
        with db_cursor() as cur:
            cur.execute("SELECT * FROM scheduled_jobs WHERE enabled=1")
            rows = [dict(x) for x in cur.fetchall()]
        for row in rows:
            payload = json.loads(row.get("action_payload") or "{}")
            self._schedule_aps_job(row["id"], row["schedule"], row["action"], payload)

    def create_job(self, name: str, schedule: str, action: str, action_payload: Optional[Dict[str, Any]] = None, enabled: bool = True) -> Dict[str, Any]:
        action_payload = action_payload or {}
        schedule = self.parse_natural_language(schedule)
        if not self.validate_cron(schedule):
            raise ValueError("Invalid cron schedule")

        next_run = self._next_run(schedule)
        ts = now_iso()
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO scheduled_jobs(name, schedule, action, action_payload, enabled, last_run, next_run, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, schedule, action, json.dumps(action_payload), int(enabled), None, next_run, ts, ts),
            )
            job_id = cur.lastrowid

        if enabled and self.started:
            self._schedule_aps_job(job_id, schedule, action, action_payload)

        return self.get_job(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM scheduled_jobs ORDER BY id DESC")
            rows = [dict(x) for x in cur.fetchall()]
        for r in rows:
            r["action_payload"] = json.loads(r.get("action_payload") or "{}")
            r["enabled"] = bool(r.get("enabled", 0))
        return rows

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM scheduled_jobs WHERE id=?", (job_id,))
            row = cur.fetchone()
        if not row:
            return None
        out = dict(row)
        out["action_payload"] = json.loads(out.get("action_payload") or "{}")
        out["enabled"] = bool(out.get("enabled", 0))
        return out

    def update_job(self, job_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        job = self.get_job(job_id)
        if not job:
            return None

        name = data.get("name", job["name"])
        schedule = self.parse_natural_language(data.get("schedule", job["schedule"]))
        action = data.get("action", job["action"])
        action_payload = data.get("action_payload", job.get("action_payload", {}))
        enabled = bool(data.get("enabled", job.get("enabled", True)))

        if not self.validate_cron(schedule):
            raise ValueError("Invalid cron schedule")

        next_run = self._next_run(schedule) if enabled else None

        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE scheduled_jobs
                SET name=?, schedule=?, action=?, action_payload=?, enabled=?, next_run=?, updated_at=?
                WHERE id=?
                """,
                (name, schedule, action, json.dumps(action_payload), int(enabled), next_run, now_iso(), job_id),
            )

        try:
            self.scheduler.remove_job(f"scheduled-job-{job_id}")
        except Exception:
            pass

        if enabled and self.started:
            self._schedule_aps_job(job_id, schedule, action, action_payload)

        return self.get_job(job_id)

    def delete_job(self, job_id: int) -> bool:
        try:
            self.scheduler.remove_job(f"scheduled-job-{job_id}")
        except Exception:
            pass

        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))
            return cur.rowcount > 0

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute(
                "SELECT h.*, j.name as job_name FROM scheduler_history h LEFT JOIN scheduled_jobs j ON j.id=h.job_id ORDER BY h.id DESC LIMIT ?",
                (limit,),
            )
            rows = [dict(x) for x in cur.fetchall()]
        for r in rows:
            r["output"] = json.loads(r.get("output") or "{}")
        return rows
