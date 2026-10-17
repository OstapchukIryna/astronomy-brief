import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.domain.apod import MediaType


class BriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: dt.date
    title: str
    explanation: str
    media_type: MediaType
    url: str
    hd_url: str | None
    credit: str | None


class ExplanationResponse(BaseModel):
    date: dt.date
    explanation: str


class FactsResponse(BaseModel):
    date: dt.date
    facts: list[str]
