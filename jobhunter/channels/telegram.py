"""Telegram channel over the official Bot HTTP API.

Secrets come from the environment only and are never written to the repo
or logged: JOBHUNTER_TELEGRAM_BOT_TOKEN and JOBHUNTER_TELEGRAM_CHAT_ID.

The transport is injectable and update parsing is pure, so the channel is
fully testable offline. Polling uses getUpdates with a persisted offset:
no webhook or public URL needed.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple

from .base import Channel, Decision

BASE = "https://api.telegram.org"

_DECISION_RE = re.compile(r"^\s*(approve|skip)\s+(\S+)", re.IGNORECASE)

Transport = Callable[[str, Dict[str, str], bytes, float], dict]


def urllib_transport(url: str, headers: Dict[str, str], payload: bytes,
                     timeout: float) -> dict:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class TelegramChannel(Channel):
    name = "telegram"

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None,
                 state_path: Optional[str] = None,
                 transport: Optional[Transport] = None, timeout: float = 30.0):
        self._token = token if token is not None else os.environ.get(
            "JOBHUNTER_TELEGRAM_BOT_TOKEN", "").strip()
        if not self._token:
            raise RuntimeError(
                "no Telegram bot token: set JOBHUNTER_TELEGRAM_BOT_TOKEN "
                "(see README, 'Telegram channel')")
        self._chat_id = chat_id if chat_id is not None else os.environ.get(
            "JOBHUNTER_TELEGRAM_CHAT_ID", "").strip()
        if not self._chat_id:
            raise RuntimeError(
                "no Telegram chat id: set JOBHUNTER_TELEGRAM_CHAT_ID "
                "(see README, 'Telegram channel')")
        self._state_path = state_path
        self._transport = transport or urllib_transport
        self._timeout = timeout

    def _call(self, method: str, params: dict) -> dict:
        url, headers, payload = self.build_request(method, params)
        data = self._transport(url, headers, payload, self._timeout)
        return self.parse_response(method, data)

    def build_request(self, method: str, params: dict):
        url = f"{BASE}/bot{self._token}/{method}"
        headers = {"Content-Type": "application/json"}
        payload = json.dumps(params).encode("utf-8")
        return url, headers, payload

    @staticmethod
    def parse_response(method: str, data: dict) -> dict:
        if not data.get("ok"):
            raise RuntimeError(
                f"telegram {method} failed: {data.get('description', data)}")
        return data.get("result") or {}

    def send_alert(self, text: str) -> str:
        result = self._call("sendMessage",
                            {"chat_id": self._chat_id, "text": text})
        return str(result.get("message_id", ""))

    @staticmethod
    def parse_updates(updates: List[dict]) -> Tuple[List[Decision], Optional[int]]:
        """Pull approve/skip decisions out of raw getUpdates results."""
        decisions: List[Decision] = []
        max_id: Optional[int] = None
        for update in updates:
            uid = update.get("update_id")
            if uid is not None:
                max_id = uid if max_id is None else max(max_id, uid)
            text = (update.get("message") or {}).get("text", "") or ""
            match = _DECISION_RE.match(text)
            if match:
                decisions.append(Decision(verdict=match.group(1).lower(),
                                          item_id=match.group(2),
                                          text=text.strip()))
        return decisions, max_id

    def poll_decisions(self) -> List[Decision]:
        offset = self._load_offset()
        params: dict = {"timeout": 0, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset
        updates = self._call("getUpdates", params)
        if not isinstance(updates, list):
            updates = []
        decisions, max_id = self.parse_updates(updates)
        if max_id is not None:
            self._save_offset(max_id + 1)
        return decisions

    def _load_offset(self) -> int:
        if self._state_path and os.path.exists(self._state_path):
            try:
                with open(self._state_path, "r", encoding="utf-8") as fh:
                    return int(json.load(fh).get("offset", 0))
            except (OSError, ValueError):
                return 0
        return 0

    def _save_offset(self, offset: int) -> None:
        if not self._state_path:
            return
        with open(self._state_path, "w", encoding="utf-8") as fh:
            json.dump({"offset": offset}, fh)
