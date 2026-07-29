from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from py.cache import InsightCache


class CacheTests(unittest.TestCase):
    def test_corrupt_disk_json_returns_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = InsightCache(Path(tmp))
            path = cache._path("bad-key")
            path.write_text("{not-json", encoding="utf-8")
            self.assertIsNone(cache.get_json("bad-key"))
            self.assertFalse(path.exists())

    def test_memory_cap_evicts_oldest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = InsightCache(Path(tmp))
            # Force a tiny cap for the test.
            import py.cache as cache_mod

            original = cache_mod.MEMORY_MAX_ENTRIES
            cache_mod.MEMORY_MAX_ENTRIES = 2
            try:
                cache.set_json("a", {"n": 1})
                cache.set_json("b", {"n": 2})
                cache.set_json("c", {"n": 3})
                self.assertEqual(len(cache.memory), 2)
                self.assertNotIn("a", cache.memory)
            finally:
                cache_mod.MEMORY_MAX_ENTRIES = original

    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = InsightCache(Path(tmp))
            cache.set_json("k", {"ok": True})
            self.assertEqual(cache.get_json("k"), {"ok": True})
            # Drop memory and reload from disk.
            cache.memory.clear()
            self.assertEqual(cache.get_json("k"), {"ok": True})


class BBoxValidationTests(unittest.TestCase):
    def test_validate_bbox(self) -> None:
        from fastapi import HTTPException

        from py.bbox import validate_bbox

        w, s, e, n = validate_bbox(153.0, -27.5, 153.1, -27.4)
        self.assertEqual((w, s, e, n), (153.0, -27.5, 153.1, -27.4))

        with self.assertRaises(HTTPException) as missing:
            validate_bbox(None, -27.5, 153.1, -27.4)
        self.assertEqual(missing.exception.status_code, 400)

        with self.assertRaises(HTTPException) as order:
            validate_bbox(153.2, -27.5, 153.1, -27.4)
        self.assertEqual(order.exception.status_code, 400)

        with self.assertRaises(HTTPException) as huge:
            validate_bbox(150.0, -30.0, 155.0, -25.0)
        self.assertEqual(huge.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
