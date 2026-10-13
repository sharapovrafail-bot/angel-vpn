#!/usr/bin/env python3
"""Derive the Angel VPN Android signing key deterministically from a secret seed.

The same seed always produces the same RSA key and the same certificate, so
APKs built on different CI runs share one signature and installed apps can be
updated. Nothing secret is stored in the repository: the seed comes from the
repository secrets.

Usage: SEED=... derive_keystore.py <out.p12>
Prints the keystore password (also the key password) and the alias to stdout as
"pass=<hex>" and "alias=angelvpn" lines for $GITHUB_OUTPUT.
"""
import datetime
import hashlib
import os
import sys

from Crypto.PublicKey import RSA
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

ALIAS = "angelvpn"


class DeterministicRandom:
    """SHAKE-256 stream used as the RNG for RSA key generation."""

    def __init__(self, seed: bytes):
        self._seed = seed
        self._counter = 0
        self._buf = b""

    def __call__(self, n: int) -> bytes:
        while len(self._buf) < n:
            block = hashlib.shake_256(self._seed + self._counter.to_bytes(8, "big")).digest(4096)
            self._counter += 1
            self._buf += block
        out, self._buf = self._buf[:n], self._buf[n:]
        return out


def main():
    seed_text = os.environ.get("SEED", "")
    if len(seed_text.strip()) < 16:
        sys.exit("SEED is empty or too short")
    seed = hashlib.sha512(b"angel-vpn-android-signing-v1|" + seed_text.encode()).digest()

    rsa = RSA.generate(4096, randfunc=DeterministicRandom(seed))
    key = serialization.load_der_private_key(rsa.export_key(format="DER"), password=None)

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Angel VPN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Angel VPN"),
    ])
    serial = int.from_bytes(hashlib.sha256(seed + b"serial").digest()[:16], "big") >> 1
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(serial)
        .not_valid_before(datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))
        .not_valid_after(datetime.datetime(2126, 1, 1, tzinfo=datetime.timezone.utc))
        .sign(key, hashes.SHA256())  # PKCS#1 v1.5 -> deterministic signature
    )

    password = hashlib.sha256(seed + b"password").hexdigest()
    p12 = pkcs12.serialize_key_and_certificates(
        ALIAS.encode(), key, cert, None,
        serialization.BestAvailableEncryption(password.encode()),
    )
    with open(sys.argv[1], "wb") as f:
        f.write(p12)

    print(f"alias={ALIAS}")
    print(f"pass={password}")
    print("cert_sha256=" + cert.fingerprint(hashes.SHA256()).hex(), file=sys.stderr)


if __name__ == "__main__":
    main()
