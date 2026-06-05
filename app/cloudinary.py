import hashlib
import hmac
import time

from fastapi import HTTPException, Request, status

from app.config import Settings


SIGNATURE_HEADER = "x-cld-signature"
TIMESTAMP_HEADER = "x-cld-timestamp"


def verify_notification_signature(raw_body: bytes, signature: str, timestamp: str, api_secret: str) -> bool:
    signed = raw_body + timestamp.encode("utf-8") + api_secret.encode("utf-8")
    sha1_digest = hashlib.sha1(signed).hexdigest()
    sha256_digest = hashlib.sha256(signed).hexdigest()
    return hmac.compare_digest(signature, sha1_digest) or hmac.compare_digest(signature, sha256_digest)


async def enforce_cloudinary_signature(request: Request, settings: Settings) -> bytes:
    raw_body = await request.body()
    if not settings.cloudinary_signature_required:
        return raw_body

    if not settings.cloudinary_api_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary signature validation is required but CLOUDINARY_API_SECRET is not configured.",
        )

    signature = request.headers.get(SIGNATURE_HEADER)
    timestamp = request.headers.get(TIMESTAMP_HEADER)
    if not signature or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Cloudinary signature headers.",
        )

    try:
        timestamp_int = int(timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Cloudinary timestamp.",
        ) from exc

    age = abs(int(time.time()) - timestamp_int)
    if age > settings.cloudinary_signature_tolerance_seconds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired Cloudinary signature.",
        )

    if not verify_notification_signature(raw_body, signature, timestamp, settings.cloudinary_api_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Cloudinary signature.",
        )

    return raw_body
