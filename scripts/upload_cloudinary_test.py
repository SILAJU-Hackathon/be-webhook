import hashlib
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()

    image_path = Path(os.getenv("CLOUDINARY_TEST_IMAGE", "img/DSC06041.JPG"))
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    notification_url = os.getenv("WEBHOOK_PUBLIC_URL")

    missing = [
        name
        for name, value in {
            "CLOUDINARY_CLOUD_NAME": cloud_name,
            "CLOUDINARY_API_KEY": api_key,
            "CLOUDINARY_API_SECRET": api_secret,
        }.items()
        if not value
    ]
    if missing:
        print(f"Missing env: {', '.join(missing)}", file=sys.stderr)
        return 1

    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        return 1

    timestamp = str(int(time.time()))
    params: dict[str, str] = {
        "api_key": api_key,
        "context": "Id=test-fastapi-webhook|latitude=-6.200000|longitude=106.816666|description=fastapi webhook smoke test",
        "timestamp": timestamp,
    }
    if notification_url:
        params["notification_url"] = notification_url

    params["signature"] = sign_upload_params(params, api_secret)

    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    with image_path.open("rb") as image:
        files = {"file": (image_path.name, image, "image/jpeg")}
        response = httpx.post(url, data=params, files=files, timeout=120)

    if response.is_error:
        print(f"Cloudinary upload failed: HTTP {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return 1

    data = response.json()
    print("Upload OK")
    print(f"public_id: {data.get('public_id')}")
    print(f"secure_url: {data.get('secure_url')}")
    print(f"notification_url: {notification_url or '(not set)'}")
    return 0


def sign_upload_params(params: dict[str, str], api_secret: str) -> str:
    signable = {
        key: value
        for key, value in params.items()
        if key not in {"api_key", "file", "resource_type", "cloud_name", "signature"} and value
    }
    payload = "&".join(f"{key}={signable[key]}" for key in sorted(signable))
    return hashlib.sha1(f"{payload}{api_secret}".encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
