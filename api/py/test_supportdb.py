from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from py.supportdb import Supporter, connect, init_schema, is_supporter, record


def supporter(**overrides) -> Supporter:
    fields = {
        "checkout_session_id": "cs_test_123",
        "clerk_user_id": "user_abc",
        "email": "driver@example.com",
        "amount_cents": 500,
        "currency": "aud",
    }
    fields.update(overrides)
    return Supporter(**fields)


class SupportDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self._tmp.name) / "supporters.db")
        init_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()
        self._tmp.cleanup()

    def test_replayed_webhooks_do_not_duplicate_a_payment(self) -> None:
        self.assertTrue(record(self.conn, supporter()))
        self.assertFalse(record(self.conn, supporter()))

    def test_finds_a_supporter_by_clerk_id(self) -> None:
        record(self.conn, supporter())
        self.assertTrue(
            is_supporter(self.conn, clerk_user_id="user_abc", email=None)
        )

    def test_finds_a_supporter_who_paid_before_signing_in(self) -> None:
        record(self.conn, supporter(clerk_user_id=None))
        self.assertTrue(
            is_supporter(self.conn, clerk_user_id="user_new", email="Driver@Example.com")
        )

    def test_unknown_people_are_not_supporters(self) -> None:
        record(self.conn, supporter())
        self.assertFalse(
            is_supporter(self.conn, clerk_user_id="user_other", email="nope@example.com")
        )

    def test_anonymous_callers_are_never_supporters(self) -> None:
        record(self.conn, supporter())
        self.assertFalse(is_supporter(self.conn, clerk_user_id=None, email=None))


if __name__ == "__main__":
    unittest.main()
