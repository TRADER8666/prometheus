from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = payload.get("action")
    try:
        from icalendar import Calendar, Event  # type: ignore
    except Exception as e:
        return {"ok": False, "error": f"icalendar not installed: {e}"}

    try:
        if action == "create_ics":
            title = payload.get("title", "Event")
            start = payload.get("start", datetime.utcnow().isoformat())
            end = payload.get("end", datetime.utcnow().isoformat())
            path = Path(payload.get("path", "/tmp/event.ics"))

            cal = Calendar()
            ev = Event()
            ev.add("summary", title)
            ev.add("dtstart", datetime.fromisoformat(start))
            ev.add("dtend", datetime.fromisoformat(end))
            cal.add_component(ev)
            path.write_bytes(cal.to_ical())
            return {"ok": True, "path": str(path)}

        if action == "parse_ics":
            path = Path(payload["path"])
            cal = Calendar.from_ical(path.read_bytes())
            events = []
            for comp in cal.walk():
                if comp.name == "VEVENT":
                    events.append(
                        {
                            "summary": str(comp.get("summary", "")),
                            "start": str(comp.get("dtstart", "")),
                            "end": str(comp.get("dtend", "")),
                        }
                    )
            return {"ok": True, "events": events}

        return {"ok": False, "error": "Unknown action"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
