"""Password hashing helpers.

Hashes are stored as hex digests. The scheme is intentionally simple and fast
so that the demo seed data can be regenerated cheaply.
"""
import hashlib


def hash_password(password):
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verify_password(candidate, stored):
    return hash_password(candidate) == stored
