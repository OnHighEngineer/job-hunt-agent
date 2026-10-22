"""RSS/Atom job feeds. Stdlib XML parsing; pass a URL, a file path, or raw XML."""
from __future__ import annotations

import time
import urllib.request
from datetime import datetime
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Iterable, Optional

from ..models import JobPosting
from .base import JobSource


def _company_from_url(url: str) -> str:
    """Best-effort company hint from a job URL.

    Board URLs usually carry the company as the first path segment
    (boards.greenhouse.io/acme/..., jobs.lever.co/acme/...). Falls back
    to the second-level domain label.
    """
    host_path = url.split("://", 1)[-1]
    parts = [p for p in host_path.split("/") if p]
    if not parts:
        return ""
    if len(parts) > 1 and parts[1].lower() not in ("jobs", "job", "careers"):
        return parts[1]
    labels = parts[0].split(".")
    return labels[-2] if len(labels) >= 2 else parts[0]



def _parse_date(raw: str):
    """RFC 822 (RSS) or ISO 8601 (Atom) -> epoch seconds, else None."""
    try:
        return parsedate_to_datetime(raw).timestamp()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None

def _text(elem, *names) -> str:
    for child in elem.iter():
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names and child.text:
            return child.text.strip()
    return ""


class RSSSource(JobSource):
    def __init__(self, feed: str, name: str = "rss",
                 now: Optional[float] = None, timeout: float = 30.0):
        self._feed = feed
        self.name = name
        self._now = now if now is not None else time.time()
        self._timeout = timeout

    def _load(self) -> str:
        if self._feed.lstrip().startswith("<"):
            return self._feed
        if self._feed.startswith(("http://", "https://")):
            with urllib.request.urlopen(self._feed, timeout=self._timeout) as resp:
                return resp.read().decode("utf-8")
        with open(self._feed, "r", encoding="utf-8") as fh:
            return fh.read()

    def fetch(self) -> Iterable[JobPosting]:
        root = ET.fromstring(self._load())
        items = [e for e in root.iter()
                 if e.tag.rsplit("}", 1)[-1].lower() in ("item", "entry")]
        postings = []
        for item in items:
            title = _text(item, "title")
            link = _text(item, "link")
            if not link:  # Atom links live in an href attribute
                for child in item.iter():
                    if (child.tag.rsplit("}", 1)[-1].lower() == "link"
                            and child.get("href")):
                        link = child.get("href")
                        break
            pub = _text(item, "pubdate", "published", "updated")
            days = None
            if pub:
                ts = _parse_date(pub)
                if ts is not None:
                    days = max(0, int((self._now - ts) // 86400))
            if title and link:
                company = _text(item, "company", "author") or _company_from_url(link)
                postings.append(JobPosting(
                    title=title, company=company,
                    url=link, source=self.name,
                    description=_text(item, "description", "summary", "content"),
                    posted_days_ago=days))
        return postings
