import pytest
from fastapi import FastAPI

ERROR_SCHEMA = {"$ref": "#/components/schemas/ErrorResponse"}


@pytest.mark.parametrize(
    ("path", "expected_statuses"),
    [
        pytest.param("/briefs", {"400", "503"}, id="history"),
        pytest.param("/briefs/{date}", {"400", "404", "502", "503"}, id="brief"),
        pytest.param(
            "/briefs/{date}/explanation",
            {"400", "404", "502", "503"},
            id="explanation",
        ),
        pytest.param("/briefs/{date}/facts", {"400", "404", "502", "503"}, id="facts"),
    ],
)
def test_documents_each_route_error_with_the_error_model(
    app: FastAPI, path: str, expected_statuses: set[str]
) -> None:
    responses = app.openapi()["paths"][path]["get"]["responses"]
    documented_errors = {
        code: response["content"]["application/json"]["schema"]
        for code, response in responses.items()
        if code not in ("200", "422")
    }

    assert documented_errors == dict.fromkeys(expected_statuses, ERROR_SCHEMA)
