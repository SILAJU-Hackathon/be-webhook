import json
from typing import Any

from fastapi import HTTPException, status

from app.models import ParsedWebhookData, PipelineRequest, PipelineResponse, SupabaseUpdate
from app.services import PipelineClient, SupabaseClient


def parse_cloudinary_payload(raw_body: bytes) -> ParsedWebhookData:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        ) from exc

    body = payload.get("body", payload)
    if not isinstance(body, dict):
        body = {}

    context = _as_dict(body.get("context"))
    custom = _as_dict(context.get("custom"))

    return ParsedWebhookData(
        id=custom.get("Id") or None,
        latitude=_to_float_or_none(custom.get("latitude")),
        longitude=_to_float_or_none(custom.get("longitude")),
        description=custom.get("description") or "",
        before_img_url=body.get("secure_url") or "",
    )


async def run_webhook_workflow(
    parsed: ParsedWebhookData,
    pipeline_client: PipelineClient,
    supabase_client: SupabaseClient,
) -> PipelineResponse | None:
    if not parsed.id:
        return None

    pipeline_response = await pipeline_client.process_url(
        PipelineRequest(
            lan=parsed.latitude,
            lon=parsed.longitude,
            img_location=parsed.before_img_url,
        )
    )

    await supabase_client.update_report(
        parsed.id,
        SupabaseUpdate(
            destruct_class=pipeline_response.classification.condition,
            location_score=pipeline_response.priority_score,
            total_score=pipeline_response.max_impact,
        ),
    )

    return pipeline_response


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _to_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
