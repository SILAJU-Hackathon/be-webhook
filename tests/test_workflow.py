import hashlib
import json
import time

from fastapi.testclient import TestClient

from app.cloudinary import verify_notification_signature
from app.config import Settings, get_settings
from app.main import create_app
from app.workflow import parse_cloudinary_payload


def test_parse_cloudinary_payload_matches_n8n_template() -> None:
    raw = json.dumps(
        {
            "body": {
                "secure_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                "context": {
                    "custom": {
                        "Id": "report-1",
                        "latitude": "-6.2",
                        "longitude": "106.8",
                        "description": "jalan rusak",
                    }
                },
            }
        }
    ).encode()

    parsed = parse_cloudinary_payload(raw)

    assert parsed.id == "report-1"
    assert parsed.latitude == -6.2
    assert parsed.longitude == 106.8
    assert parsed.description == "jalan rusak"
    assert parsed.before_img_url == "https://res.cloudinary.com/demo/image/upload/sample.jpg"


def test_cloudinary_signature_verification_uses_raw_body_timestamp_and_secret() -> None:
    raw_body = b'{"public_id":"sample"}'
    timestamp = "1315060510"
    secret = "abcd"
    signature = hashlib.sha1(raw_body + timestamp.encode() + secret.encode()).hexdigest()

    assert verify_notification_signature(raw_body, signature, timestamp, secret)


def test_webhook_skips_missing_id_without_external_calls() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        cloudinary_api_secret="secret",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    client = TestClient(app)
    body = json.dumps({"body": {"context": {"custom": {}}, "secure_url": ""}}, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    signature = hashlib.sha1(body + timestamp.encode() + b"secret").hexdigest()

    response = client.post(
        "/cloudinary-trigger",
        content=body,
        headers={
            "content-type": "application/json",
            "x-cld-signature": signature,
            "x-cld-timestamp": timestamp,
        },
    )

    assert response.status_code == 202
    assert response.json() == {"status": "skipped", "id": None, "pipeline_url": None}
