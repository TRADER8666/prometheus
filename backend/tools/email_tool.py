from email.mime.text import MIMEText
from typing import Any, Dict
import imaplib
import smtplib


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = payload.get("action")
    try:
        if action == "send":
            smtp_host = payload["smtp_host"]
            smtp_port = int(payload.get("smtp_port", 587))
            username = payload["username"]
            password = payload["password"]
            to = payload["to"]
            subject = payload.get("subject", "")
            body = payload.get("body", "")

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = username
            msg["To"] = to

            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            return {"ok": True}

        if action == "search_inbox":
            imap_host = payload["imap_host"]
            username = payload["username"]
            password = payload["password"]
            query = payload.get("query", "ALL")
            limit = int(payload.get("limit", 10))

            with imaplib.IMAP4_SSL(imap_host) as imap:
                imap.login(username, password)
                imap.select("INBOX")
                typ, data = imap.search(None, query)
                ids = data[0].split()[-limit:]
                return {"ok": True, "email_ids": [x.decode() for x in ids]}

        return {"ok": False, "error": "Unknown action"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
