"""RFC 6238 TOTP (SHA-1, 30 s, 6 digits) for the dedicated 3LO test user's authenticator-app registration.
The seed lives only in tests/.entra-totp.env (gitignored). Usage: python3 tests/totp.py  -> prints the current code."""
from __future__ import annotations
import base64, hashlib, hmac, os, struct, time


def code(secret_b32: str, at: float | None = None) -> str:
    key = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    h = hmac.new(key, struct.pack(">Q", int((at or time.time()) // 30)), hashlib.sha1).digest()
    o = h[-1] & 15
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


def current() -> str:
    env = dict(l.strip().split("=", 1) for l in open(os.path.join(os.path.dirname(__file__), ".entra-totp.env")) if "=" in l)
    return code(env["ENTRA_TOTP_LO3USER"])


if __name__ == "__main__":
    print(current())
