from urllib.parse import quote, urlparse

import httpx
from fastapi import HTTPException, status

from app.config import Settings
from app.models import PipelineRequest, PipelineResponse, SupabaseUpdate


class PipelineClient:
    _image_field_names = ("image", "file", "img")

    def __init__(self, settings: Settings) -> None:
        self._base_url = str(settings.ai_pipeline_url).rstrip("/")
        self._timeout = settings.ai_pipeline_timeout_seconds

    async def process_url(self, payload: PipelineRequest) -> PipelineResponse:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            image = await self._download_image(client, payload.img_location)

            try:
                response = await self._post_process_form(client, payload, image)
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"AI pipeline request failed: {exc}",
                ) from exc

        return PipelineResponse.model_validate(response.json())

    async def _download_image(self, client: httpx.AsyncClient, image_url: str) -> tuple[str, bytes, str]:
        try:
            response = await client.get(image_url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to download Cloudinary image: {exc}",
            ) from exc

        content = response.content
        if not content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Downloaded Cloudinary image is empty.",
            )

        content_type = response.headers.get("content-type", "application/octet-stream").split(";")[0]
        filename = _filename_from_url(image_url)
        return filename, content, content_type

    async def _post_process_form(
        self,
        client: httpx.AsyncClient,
        payload: PipelineRequest,
        image: tuple[str, bytes, str],
    ) -> httpx.Response:
        last_response: httpx.Response | None = None
        data = {
            "lan": str(payload.lan),
            "lon": str(payload.lon),
        }

        for field_name in self._image_field_names:
            filename, content, content_type = image
            files = {
                field_name: (filename, content, content_type),
            }
            response = await client.post(f"{self._base_url}/process", data=data, files=files)
            if response.status_code != 422:
                response.raise_for_status()
                return response

            last_response = response

        if last_response is not None:
            last_response.raise_for_status()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI pipeline did not return a response.",
        )


def _filename_from_url(image_url: str) -> str:
    path = urlparse(image_url).path
    filename = path.rsplit("/", 1)[-1].strip()
    return filename or "cloudinary-image.jpg"


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
