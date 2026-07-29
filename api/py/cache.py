from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")

TTL_SECS = 24 * 60 * 60


class InsightCache:
    def __init__(self, directory: Path) -> None:
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.memory: dict[str, tuple[float, str]] = {}

    def _path(self, key: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", key)
        return self.dir / f"{safe}.json"

    def get_json(self, key: str) -> Any | None:
        now = time.time()
        if key in self.memory:
            ts, raw = self.memory[key]
            if now - ts < TTL_SECS:
                return json.loads(raw)
            del self.memory[key]

        path = self._path(key)
        if not path.exists():
            return None
        age = now - path.stat().st_mtime
        if age >= TTL_SECS:
            path.unlink(missing_ok=True)
            return None
        raw = path.read_text(encoding="utf-8")
        self.memory[key] = (now, raw)
        return json.loads(raw)

    def set_json(self, key: str, value: Any) -> None:
        raw = json.dumps(value, separators=(",", ":"))
        self.memory[key] = (time.time(), raw)
        self._path(key).write_text(raw, encoding="utf-8")
