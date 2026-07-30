from __future__ import annotations

import unittest

from py.clerkauth import bearer_token, claim_email
from py.stripepay import (
    INTEGRATION_IDENTIFIER,
    build_session_params,
    clean_email,
    supporter_from_event,
)


def paid_event(**overrides) -> dict:
    session = {
        "id": "cs_test_123",
        "payment_status": "paid",
        "amount_total": 500,
        "currency": "aud",
        "customer_details": {"email": "Driver@Example.com"},
        "metadata": {"clerk_user_id": "user_abc"},
    }
    session.update(overrides)
    return {"type": "checkout.session.completed", "data": {"object": session}}


class SessionParamTests(unittest.TestCase):
    def test_five_dollar_donation_in_an_embedded_dialog(self) -> None:
        params = build_session_params(
            amount=500, currency_code="aud", name="Supporter coffee"
        )
        self.assertEqual(params["mode"], "payment")
        self.assertEqual(params["ui_mode"], "embedded_page")
        self.assertEqual(params["redirect_on_completion"], "never")
        self.assertEqual(params["submit_type"], "donate")
        price = params["line_items"][0]["price_data"]
        self.assertEqual(price["unit_amount"], 500)
        self.assertEqual(price["currency"], "aud")
        self.assertEqual(params["integration_identifier"], INTEGRATION_IDENTIFIER)

    def test_leaves_payment_methods_to_the_dashboard(self) -> None:
        params = build_session_params(amount=500, currency_code="aud", name="Coffee")
        self.assertNotIn("payment_method_types", params)

    def test_omits_email_and_metadata_for_anonymous_payers(self) -> None:
        params = build_session_params(amount=500, currency_code="aud", name="Coffee")
        self.assertNotIn("customer_email", params)
        self.assertNotIn("metadata", params)

    def test_prefills_email_and_tags_the_clerk_user(self) -> None:
        params = build_session_params(
            amount=500,
            currency_code="aud",
            name="Coffee",
            email="driver@example.com",
            clerk_user_id="user_abc",
        )
        self.assertEqual(params["customer_email"], "driver@example.com")
        self.assertEqual(params["metadata"], {"clerk_user_id": "user_abc"})


class EmailTests(unittest.TestCase):
    def test_normalises_case_and_padding(self) -> None:
        self.assertEqual(clean_email("  Driver@Example.com "), "driver@example.com")

    def test_rejects_junk(self) -> None:
        for bad in [None, "", "   ", "driver", "driver@localhost", "a b@example.com"]:
            self.assertIsNone(clean_email(bad), bad)

    def test_rejects_oversized_input(self) -> None:
        self.assertIsNone(clean_email("a" * 320 + "@example.com"))


class EventMappingTests(unittest.TestCase):
    def test_maps_a_paid_session(self) -> None:
        supporter = supporter_from_event(paid_event())
        assert supporter is not None
        self.assertEqual(supporter.checkout_session_id, "cs_test_123")
        self.assertEqual(supporter.clerk_user_id, "user_abc")
        self.assertEqual(supporter.email, "driver@example.com")
        self.assertEqual(supporter.amount_cents, 500)
        self.assertEqual(supporter.currency, "aud")

    def test_keeps_anonymous_payments(self) -> None:
        supporter = supporter_from_event(paid_event(metadata={}))
        assert supporter is not None
        self.assertIsNone(supporter.clerk_user_id)

    def test_ignores_unpaid_and_unrelated_events(self) -> None:
        self.assertIsNone(supporter_from_event(paid_event(payment_status="unpaid")))
        self.assertIsNone(supporter_from_event({"type": "customer.created", "data": {}}))
        self.assertIsNone(supporter_from_event(paid_event(id="")))


class BearerTokenTests(unittest.TestCase):
    def test_accepts_a_bearer_header(self) -> None:
        self.assertEqual(bearer_token("Bearer abc.def.ghi"), "abc.def.ghi")

    def test_rejects_other_schemes_and_blanks(self) -> None:
        for bad in [None, "", "Basic abc", "Bearer", "Bearer   "]:
            self.assertIsNone(bearer_token(bad), bad)

    def test_reads_email_only_from_known_claims(self) -> None:
        self.assertEqual(claim_email({"email": "Driver@Example.com"}), "driver@example.com")
        self.assertIsNone(claim_email({"sub": "user_abc"}))


if __name__ == "__main__":
    unittest.main()
