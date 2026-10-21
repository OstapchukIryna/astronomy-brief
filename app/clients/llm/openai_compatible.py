"""LLM client for any OpenAI-compatible chat API."""

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.clients.http import send
from app.domain.apod import ApodEntry
from app.domain.facts import Facts, InvalidFactsError
from app.domain.llm import LlmBadResponseError, LlmUnavailableError
from app.prompts import explanation, facts

MAX_ERROR_DETAIL = 200


class _Message(BaseModel):
    content: str | None = None


class _Choice(BaseModel):
    message: _Message


class _Completion(BaseModel):
    """The part of an OpenAI-compatible chat completion we use."""

    choices: list[_Choice] = Field(min_length=1)


class _FactsAnswer(BaseModel):
    facts: list[str] = Field(min_length=1)


class _ErrorInfo(BaseModel):
    message: str


class _ErrorBody(BaseModel):
    """The error body of an OpenAI-compatible API."""

    error: _ErrorInfo


class OpenAICompatibleLlmClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
    ) -> None:
        self._http = http
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model
        self._temperature = temperature

    async def explain(self, entry: ApodEntry) -> str:
        """Return a beginner-friendly explanation based only on the retrieved APOD text."""
        content = await self._complete(
            explanation.SYSTEM, explanation.user_message(entry.title, entry.explanation)
        )
        text = content.strip()
        if not text:
            raise LlmBadResponseError("LLM returned an empty explanation")
        return text

    async def extract_facts(self, entry: ApodEntry) -> Facts:
        """Return interesting facts about the APOD's topic."""
        content = await self._complete(
            facts.SYSTEM,
            facts.user_message(entry.title, entry.explanation),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "facts",
                    "schema": _FactsAnswer.model_json_schema(),
                },
            },
        )
        try:
            answer = _FactsAnswer.model_validate_json(content)
        except ValidationError as error:
            raise LlmBadResponseError(
                "LLM returned facts in an unexpected format"
            ) from error
        try:
            return Facts.from_candidates(answer.facts)
        except InvalidFactsError as error:
            raise LlmBadResponseError(
                f"LLM returned unusable facts: {error}"
            ) from error

    async def _complete(
        self,
        system: str,
        user: str,
        response_format: dict[str, object] | None = None,
    ) -> str:
        """Send one chat request and return the answer text."""
        body: dict[str, object] = {
            "model": self._model,
            "temperature": self._temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_format is not None:
            body["response_format"] = response_format

        response = await send(
            lambda: self._http.post(self._url, json=body, headers=self._headers),
            what="LLM",
            unavailable=LlmUnavailableError,
            bad_response=LlmBadResponseError,
            detail=_error_detail,
        )
        if response.status_code != httpx.codes.OK:
            raise LlmBadResponseError(
                f"LLM returned {response.status_code}{_error_detail(response)}"
            )
        try:
            completion = _Completion.model_validate_json(response.content)
        except ValidationError as error:
            raise LlmBadResponseError("LLM response has unexpected format") from error
        content = completion.choices[0].message.content
        if content is None:
            raise LlmBadResponseError("LLM returned no content")
        return content


def _error_detail(response: httpx.Response) -> str:
    """Return the provider's error message to add to ours."""
    if response.status_code in (httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN):
        return ""
    try:
        message = _ErrorBody.model_validate_json(response.content).error.message
    except ValidationError:
        return ""
    return f": {message[:MAX_ERROR_DETAIL]}"
