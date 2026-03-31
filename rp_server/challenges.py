"""In-memory challenge cache."""

from __future__ import annotations

import secrets
import threading
from typing import Dict, Tuple


class ChallengeCache:
    def __init__(self) -> None:
        self._challenges: Dict[Tuple[str, str], str] = {}
        self._lock = threading.Lock()

    def issue(self, scope: str, key: str, size: int = 32) -> str:
        challenge = secrets.token_urlsafe(size)
        with self._lock:
            self._challenges[(scope, key)] = challenge
        return challenge

    def pop(self, scope: str, key: str) -> str | None:
        with self._lock:
            return self._challenges.pop((scope, key), None)
