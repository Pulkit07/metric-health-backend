import base64
import hashlib
import hmac


def get_hash(data):
    return hashlib.sha256(str(data).encode("utf-8")).hexdigest()


def get_webhook_signature(request_body, client_secret):
    signing_key = client_secret + "&"
    encoded_body = base64.b64encode(
        hmac.new(
            signing_key.encode("utf-8"),
            request_body.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    )

    return encoded_body.decode("utf-8")
