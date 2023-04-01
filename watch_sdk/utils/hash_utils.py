import hashlib


def get_hash(data):
    return hashlib.sha256(str(data).encode("utf-8")).hexdigest()
