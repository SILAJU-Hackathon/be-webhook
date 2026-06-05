from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.config import Settings
from app.models import PipelineRequest, PipelineResponse, SupabaseUpdate


class PipelineClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = str(settings.ai_pipeline_url).rstrip("/")
        self._timeout = settings.ai_pipeline_timeout_seconds

    async def process_url(self, payload: PipelineRequest) -> PipelineResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(f"{self._base_url}/process", json=payload.model_dump())
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"AI pipeline request failed: {exc}",
                ) from exc

        return PipelineResponse.model_validate(response.json())


class SupabaseClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase is not configured.",
            )

        self._base_url = str(settings.supabase_url).rstrip("/")
        self._table = settings.supabase_table
        self._headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    async def update_report(self, report_id: str, payload: SupabaseUpdate) -> None:
        encoded_id = quote(report_id, safe="")
        url = f"{self._base_url}/rest/v1/{self._table}?id=eq.{encoded_id}"

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.patch(url, headers=self._headers, json=payload.model_dump())
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Supabase update failed: {exc}",
                ) from exc
