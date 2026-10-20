"""
Pattern 2: Stateless OAuth 2.0 PKCE & HMAC-Signed State
=======================================================
Core Interview Point:
- RFC 7636 PKCE (`S256`) prevents authorization code interception.
- Stateless HMAC-SHA256 signed `state` embeds the verifier + TTL directly into the token,
  eliminating server-side Redis/memory state across OAuth redirects and multi-worker pods.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

SECRET_KEY = b"enterprise-zero-trust-signing-secret"


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate RFC 7636 cryptographic code_verifier and S256 code_challenge."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = b64url_encode(digest)
    return verifier, challenge


def encode_stateless_state(verifier: str) -> str:
    """Embed PKCE verifier + timestamp into an HMAC-SHA256 signed state string."""
    payload = json.dumps({"v": verifier, "iat": int(time.time())}, separators=(",", ":")).encode()
    b64_payload = b64url_encode(payload)
    sig = hmac.new(SECRET_KEY, b64_payload.encode(), hashlib.sha256).digest()
    return f"{b64_payload}.{b64url_encode(sig)}"


def decode_stateless_state(state_token: str, ttl_seconds: int = 300) -> str:
    """Constant-time signature check + TTL verification; returns original PKCE verifier."""
    b64_payload, b64_sig = state_token.split(".", 1)
    expected_sig = b64url_encode(hmac.new(SECRET_KEY, b64_payload.encode(), hashlib.sha256).digest())

    if not hmac.compare_digest(b64_sig, expected_sig):
        raise ValueError("Invalid HMAC signature (CSRF / tampering detected)")

    data = json.loads(b64url_decode(b64_payload))
    if time.time() - data["iat"] > ttl_seconds:
        raise ValueError("OAuth state expired")

    return data["v"]


if __name__ == "__main__":
    verifier, challenge = generate_pkce_pair()
    state = encode_stateless_state(verifier)
    recovered_verifier = decode_stateless_state(state)

    print(f"PKCE Challenge (S256) : {challenge}")
    print(f"Stateless Signed State: {state[:45]}...")
    print(f"Verifier Roundtrip OK : {verifier == recovered_verifier}")
