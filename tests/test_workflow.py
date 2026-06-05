import hashlib
import json
import time

import httpx
import respx
from fastapi.testclient import TestClient

from app.cloudinary import verify_notification_signature
from app.config import Settings, get_settings
from app.main import create_app
from app.models import ParsedWebhookData, PipelineRequest
from app.services import PipelineClient
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
        app_name="gungfi-webhook-be",
        log_level="INFO",
        webhook_path="/cloudinary-trigger",
        ai_pipeline_url="https://pipeline.example.com",
        ai_pipeline_timeout_seconds=60,
        cloudinary_api_secret="secret",
        cloudinary_signature_required=True,
        cloudinary_signature_tolerance_seconds=7200,
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
        supabase_table="reports",
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


def test_webhook_workflow_sends_process_payload() -> None:
    from app.workflow import run_webhook_workflow

    class FakePipelineClient:
        payload = None

        async def process_url(self, payload):
            self.payload = payload
            return type(
                "PipelineResponse",
                (),
                {
                    "classification": type("Classification", (), {"condition": "rusak"})(),
                    "priority_score": 0.8,
                    "max_impact": 0.9,
                },
            )()

    class FakeSupabaseClient:
        async def update_report(self, report_id, payload):
            self.report_id = report_id
            self.payload = payload

    pipeline_client = FakePipelineClient()
    supabase_client = FakeSupabaseClient()

    import anyio

    anyio.run(
        run_webhook_workflow,
        ParsedWebhookData(
            id="report-1",
            latitude=-6.2,
            longitude=106.8,
            before_img_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
        ),
        pipeline_client,
        supabase_client,
    )

    assert pipeline_client.payload.model_dump() == {
        "lan": -6.2,
        "lon": 106.8,
        "img_location": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
    }


@respx.mock
def test_pipeline_client_posts_to_process_endpoint() -> None:
    settings = Settings(
        app_name="gungfi-webhook-be",
        log_level="INFO",
        webhook_path="/cloudinary-trigger",
        ai_pipeline_url="https://pipeline.example.com",
        ai_pipeline_timeout_seconds=60,
        cloudinary_api_secret="secret",
        cloudinary_signature_required=True,
        cloudinary_signature_tolerance_seconds=7200,
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
        supabase_table="reports",
    )
    route = respx.post("https://pipeline.example.com/process").mock(
        return_value=httpx.Response(
            200,
            json={
                "classification": {"condition": "rusak", "confidence": 0.9, "probabilities": {}},
                "priority_score": 0.8,
                "max_impact": 0.9,
            },
        )
    )

    import anyio

    anyio.run(
        PipelineClient(settings).process_url,
        PipelineRequest(
            lan=-6.2,
            lon=106.8,
            img_location="https://res.cloudinary.com/demo/image/upload/sample.jpg",
        ),
    )

    assert route.called
