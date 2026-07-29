from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")

TTL_SECS = 24 * 60 * 60
MEMORY_MAX_ENTRIES = 2048
PRUNE_EVERY_WRITES = 64


class InsightCache:
    def __init__(self, directory: Path) -> None:
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.memory: dict[str, tuple[float, str]] = {}
        self._writes = 0

    def _path(self, key: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", key)
        return self.dir / f"{safe}.json"

    def _evict_memory(self) -> None:
        overflow = len(self.memory) - MEMORY_MAX_ENTRIES
        if overflow <= 0:
            return
        oldest = sorted(self.memory.items(), key=lambda kv: kv[1][0])[:overflow]
        for key, _ in oldest:
            del self.memory[key]

    def _prune_expired_files(self) -> None:
        now = time.time()
        for path in self.dir.glob("*.json"):
            try:
                age = now - path.stat().st_mtime
                if age >= TTL_SECS:
                    path.unlink(missing_ok=True)
            except OSError:
                continue

    def get_json(self, key: str) -> Any | None:
        now = time.time()
        if key in self.memory:
            ts, raw = self.memory[key]
            if now - ts < TTL_SECS:
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    del self.memory[key]
            else:
                del self.memory[key]

        path = self._path(key)
        if not path.exists():
            return None
        try:
            age = now - path.stat().st_mtime
            if age >= TTL_SECS:
                path.unlink(missing_ok=True)
                return None
            raw = path.read_text(encoding="utf-8")
            value = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return None

        self.memory[key] = (now, raw)
        self._evict_memory()
        return value

    def set_json(self, key: str, value: Any) -> None:
        raw = json.dumps(value, separators=(",", ":"))
        self.memory[key] = (time.time(), raw)
        self._evict_memory()
        try:
            self._path(key).write_text(raw, encoding="utf-8")
        except OSError:
            pass
        self._writes += 1
        if self._writes % PRUNE_EVERY_WRITES == 0:
            self._prune_expired_files()
