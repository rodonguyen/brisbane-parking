"""Clerk session token verification.

Uses the issuer's public JWKS, so the API needs no Clerk secret key. Verification is
what makes attribution trustworthy: the browser can lie about an email, not about a
signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

try:  # payments stay optional: a missing dep must not take the map API down
    import jwt
    from jwt import PyJWKClient

    _JWT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only on hosts without pyjwt
    _JWT_AVAILABLE = False

LEEWAY_SECS = 30
EMAIL_CLAIMS = ("email", "primary_email_address", "email_address")


@dataclass(frozen=True)
class ClerkIdentity:
    user_id: str
    email: str | None


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.strip().lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def claim_email(claims: Mapping[str, Any]) -> str | None:
    """Present only when the Clerk JWT template adds it; plain sessions carry no email."""
    for name in EMAIL_CLAIMS:
        value = claims.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


class ClerkVerifier:
    def __init__(self, issuer: str) -> None:
        self.issuer = issuer.strip().rstrip("/")
        self._jwks: Any = None
        if self.issuer and _JWT_AVAILABLE:
            self._jwks = PyJWKClient(
                f"{self.issuer}/.well-known/jwks.json", cache_keys=True
            )

    @property
    def enabled(self) -> bool:
        return self._jwks is not None

    def identity(self, authorization: str | None) -> ClerkIdentity | None:
        """Returns None for anonymous, unverifiable, or expired callers."""
        token = bearer_token(authorization)
        if token is None or self._jwks is None:
            return None
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                leeway=LEEWAY_SECS,
                options={"verify_aud": False},
            )
        except Exception:
            return None
        user_id = claims.get("sub")
        if not isinstance(user_id, str) or not user_id:
            return None
        return ClerkIdentity(user_id=user_id, email=claim_email(claims))
