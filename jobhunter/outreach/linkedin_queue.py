"""LinkedIn connect-note drafts, queued for human approval.

By design there is NO send function here. LinkedIn has no official API
for connection requests and restricts accounts for automation, so the
agent drafts, the human approves, and the human sends. Approved drafts
stay local for copy-paste.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Callable, List, Optional

DRAFT = "draft"
APPROVED = "approved"
DONE = "done"  # the human marked it sent by hand


class LinkedInQueue:
    def __init__(self, path: str, now: Optional[Callable[[], float]] = None):
        self.path = path
        self._now = now or time.time
        self._items = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                self._items = json.load(fh).get("items", [])

    def draft(self, person: str, profile_url: str, note: str) -> str:
        if len(note) > 300:
            raise ValueError("LinkedIn notes are capped at 300 characters")
        item_id = uuid.uuid4().hex[:8]
        self._items.append({
            "id": item_id, "person": person, "profile_url": profile_url,
            "note": note, "status": DRAFT, "created_at": self._now()})
        self._save()
        return item_id

    def approve(self, item_id: str) -> bool:
        return self._set(item_id, DRAFT, APPROVED)

    def mark_done(self, item_id: str) -> bool:
        """Only the human's confirmation moves an approved draft to done."""
        return self._set(item_id, APPROVED, DONE)

    def _set(self, item_id: str, expect: str, new: str) -> bool:
        for item in self._items:
            if item["id"] == item_id and item["status"] == expect:
                item["status"] = new
                self._save()
                return True
        return False

    def list(self, status: Optional[str] = None) -> List[dict]:
        if status is None:
            return list(self._items)
        return [i for i in self._items if i["status"] == status]

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"items": self._items}, fh, indent=2)
