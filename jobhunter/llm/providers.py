"""Bring-your-own-key LLM adapters for OpenAI, Gemini, Grok and Claude.

Plain REST over urllib - no vendor SDKs. Keys come from the environment
via jobhunter.config.get_api_key and are never written to disk or logged.
`build_request` and `parse_response` are pure, so adapters are fully
testable offline with a fake transport.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Callable, Dict, Optional, Tuple

from ..config import DEFAULT_MODELS, get_api_key
from .base import LLMProvider

Request = Tuple[str, Dict[str, str], dict]
Transport = Callable[[str, Dict[str, str], bytes, float], dict]


def urllib_transport(url: str, headers: Dict[str, str], payload: bytes,
                     timeout: float) -> dict:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class RESTProvider(LLMProvider):
    base_url = ""
    default_model = ""

    def __init__(self, api_key: str, model: Optional[str] = None,
                 transport: Optional[Transport] = None, timeout: float = 60.0):
        if not api_key:
            raise ValueError(f"{self.name}: empty API key")
        self._api_key = api_key
        self.model = model or self.default_model
        self._transport = transport or urllib_transport
        self._timeout = timeout

    def build_request(self, prompt: str, max_tokens: int) -> Request:
        raise NotImplementedError

    def parse_response(self, data: dict) -> str:
        raise NotImplementedError

    def complete(self, prompt: str, max_tokens: int = 512) -> str:
        url, headers, body = self.build_request(prompt, max_tokens)
        data = self._transport(url, headers,
                               json.dumps(body).encode("utf-8"), self._timeout)
        return self.parse_response(data)


class _OpenAIShape(RESTProvider):
    """OpenAI-compatible chat completions (OpenAI, Grok/xAI)."""

    def build_request(self, prompt: str, max_tokens: int) -> Request:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}",
                   "Content-Type": "application/json"}
        body = {"model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens}
        return url, headers, body

    def parse_response(self, data: dict) -> str:
        return data["choices"][0]["message"]["content"]


class OpenAIProvider(_OpenAIShape):
    name = "openai"
    base_url = "https://api.openai.com"
    default_model = DEFAULT_MODELS["openai"]


class GrokProvider(_OpenAIShape):
    name = "grok"
    base_url = "https://api.x.ai"
    default_model = DEFAULT_MODELS["grok"]


class GeminiProvider(RESTProvider):
    name = "gemini"
    default_model = DEFAULT_MODELS["gemini"]

    def build_request(self, prompt: str, max_tokens: int) -> Request:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self._api_key}")
        headers = {"Content-Type": "application/json"}
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens}}
        return url, headers, body

    def parse_response(self, data: dict) -> str:
        return data["candidates"][0]["content"]["parts"][0]["text"]


class ClaudeProvider(RESTProvider):
    name = "claude"
    default_model = DEFAULT_MODELS["claude"]

    def build_request(self, prompt: str, max_tokens: int) -> Request:
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": self._api_key,
                   "anthropic-version": "2023-06-01",
                   "Content-Type": "application/json"}
        body = {"model": self.model, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]}
        return url, headers, body

    def parse_response(self, data: dict) -> str:
        return "".join(part.get("text", "") for part in data["content"])


_CLASSES = {"openai": OpenAIProvider, "gemini": GeminiProvider,
            "grok": GrokProvider, "claude": ClaudeProvider}


def get_provider(name: str, model: Optional[str] = None,
                 transport: Optional[Transport] = None,
                 api_key: Optional[str] = None) -> LLMProvider:
    """Build a provider. The key comes from the environment unless injected."""
    if name not in _CLASSES:
        raise ValueError(f"unknown provider {name!r}; choose from {sorted(_CLASSES)}")
    key = api_key if api_key is not None else get_api_key(name)
    return _CLASSES[name](api_key=key, model=model, transport=transport)
