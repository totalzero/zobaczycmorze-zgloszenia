import hmac
import hashlib
from django.conf import settings

def verify_payu_signature(request):
    signature_header = request.headers.get("OpenPayU-Signature")
    if not signature_header:
        return False

    parts = dict(
        part.split("=", 1)
        for part in signature_header.split(";")
        if "=" in part
    )

    signature = parts.get("signature")
    if not signature or not signature.startswith("sha256="):
        return False

    received = signature.replace("sha256=", "")
    secret = settings.PAYU["WEBHOOK_SECRET"].encode()
    body = request.body

    calculated = hmac.new(
        secret,
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(received, calculated)
