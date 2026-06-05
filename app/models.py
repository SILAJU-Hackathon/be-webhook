from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ParsedWebhookData(BaseModel):
    id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str = ""
    before_img_url: str = ""


class PipelineRequest(BaseModel):
    lan: float
    lon: float
    img_location: str


class PipelineClassification(BaseModel):
    model_config = ConfigDict(extra="allow")

    condition: str


class PipelineResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    classification: PipelineClassification
    priority_score: float
    max_impact: float


class SupabaseUpdate(BaseModel):
    destruct_class: str
    location_score: float
    total_score: float
    status: str = "complete"


class WebhookEnvelope(BaseModel):
    body: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    app: str


class WebhookAcceptedResponse(BaseModel):
    status: str
    id: str | None = None
    pipeline_url: HttpUrl | None = None
