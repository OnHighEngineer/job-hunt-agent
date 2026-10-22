"""Job sources. A source fetches postings; where they come from is its business."""
from __future__ import annotations

from typing import Iterable, List

from ..models import JobPosting


class JobSource:
    name = "base"

    def fetch(self) -> Iterable[JobPosting]:
        raise NotImplementedError


class StaticSource(JobSource):
    """A source from an in-memory list - fixtures and tests."""

    def __init__(self, postings: List[JobPosting], name: str = "static"):
        self._postings = postings
        self.name = name

    def fetch(self) -> Iterable[JobPosting]:
        return list(self._postings)
