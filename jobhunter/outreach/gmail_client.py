"""Mail through the official Gmail API only.

FakeMailClient keeps tests offline. GmailAPIClient talks to the real API
with a user-supplied OAuth access token from the environment; setup is
documented in the README. Sending always goes through the pipeline so the
daily cap applies.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from typing import List, Optional

from ..models import MailMessage, OutgoingMail


class MailClient:
    def search_replies(self, query: str = "", max_results: int = 20) -> List[MailMessage]:
        raise NotImplementedError

    def send(self, mail: OutgoingMail) -> str:
        """Send and return a message id."""
        raise NotImplementedError


class FakeMailClient(MailClient):
    """Offline mailbox: seeded replies, records sends. No network."""

    def __init__(self, replies: Optional[List[MailMessage]] = None):
        self.replies = list(replies or [])
        self.sent: List[OutgoingMail] = []

    def search_replies(self, query: str = "", max_results: int = 20) -> List[MailMessage]:
        if not query:
            return list(self.replies)[:max_results]
        q = query.lower()
        return [m for m in self.replies
                if q in (m.subject + m.body + m.from_addr).lower()][:max_results]

    def send(self, mail: OutgoingMail) -> str:
        self.sent.append(mail)
        return f"fake-{len(self.sent)}"


class GmailAPIClient(MailClient):
    """Minimal Gmail REST client. Token from JOBHUNTER_GMAIL_TOKEN."""

    BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, token: Optional[str] = None, timeout: float = 30.0):
        self._token = token if token is not None else os.environ.get(
            "JOBHUNTER_GMAIL_TOKEN", "").strip()
        if not self._token:
            raise RuntimeError(
                "no Gmail token: set JOBHUNTER_GMAIL_TOKEN "
                "(see README, 'Gmail setup')")
        self._timeout = timeout

    def _call(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            f"{self.BASE}{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {self._token}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def search_replies(self, query: str = "", max_results: int = 20) -> List[MailMessage]:
        q = urllib.parse.quote(query or "in:inbox -from:me")
        listing = self._call("GET", f"/messages?q={q}&maxResults={max_results}")
        messages = []
        for stub in listing.get("messages", []):
            full = self._call("GET", f"/messages/{stub['id']}?format=full")
            headers = {h["name"].lower(): h["value"]
                       for h in full.get("payload", {}).get("headers", [])}
            body = ""
            for part in full.get("payload", {}).get("parts", []):
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(
                        part["body"]["data"]).decode("utf-8", "replace")
                    break
            messages.append(MailMessage(
                from_addr=headers.get("from", ""),
                subject=headers.get("subject", ""),
                body=body,
                thread_id=full.get("threadId", ""),
                received_ts=float(full.get("internalDate", 0)) / 1000.0))
        return messages

    def send(self, mail: OutgoingMail) -> str:
        mime = (f"To: {mail.to}\r\nSubject: {mail.subject}\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n\r\n{mail.body}")
        raw = base64.urlsafe_b64encode(mime.encode("utf-8")).decode("ascii")
        result = self._call("POST", "/messages/send", {"raw": raw})
        return result.get("id", "")
