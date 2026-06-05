import logging

from fastapi import Depends, FastAPI, Request, status

from app.cloudinary import enforce_cloudinary_signature
from app.config import Settings, get_settings
from app.models import HealthResponse, WebhookAcceptedResponse
from app.services import PipelineClient, SupabaseClient
from app.workflow import parse_cloudinary_payload, run_webhook_workflow


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    app = FastAPI(title=settings.app_name)

    @app.get("/health", response_model=HealthResponse)
    async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
        return HealthResponse(status="ok", app=settings.app_name)

    @app.post(
        settings.webhook_path,
        response_model=WebhookAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def cloudinary_trigger(
        request: Request,
        settings: Settings = Depends(get_settings),
    ) -> WebhookAcceptedResponse:
        raw_body = await enforce_cloudinary_signature(request, settings)
        parsed = parse_cloudinary_payload(raw_body)

        if not parsed.id:
            return WebhookAcceptedResponse(status="skipped", id=None)

        pipeline_client = PipelineClient(settings)
        supabase_client = SupabaseClient(settings)
        await run_webhook_workflow(parsed, pipeline_client, supabase_client)

        return WebhookAcceptedResponse(
            status="complete",
            id=parsed.id,
            pipeline_url=settings.ai_pipeline_url,
        )

    return app


app = create_app()
