from __future__ import annotations

import hashlib
import hmac
import secrets


class TokenService:
    def __init__(self, secret: str) -> None:
        self._secret = secret.encode("utf-8")

    def issue(self) -> str:
        return secrets.token_urlsafe(48)

    def digest(self, token: str) -> str:
        return hmac.new(self._secret, token.encode("utf-8"), hashlib.sha256).hexdigest()

    def matches(self, token: str, expected_digest: str) -> bool:
        return hmac.compare_digest(self.digest(token), expected_digest)
