"""Turn the outcome of an httpx request into a client's own errors.

All clients classify failures the same way:
- unavailable: the request didn't get an answer (TransportError: timeout,
  connection error, broken connection) or the server is failing or
  overloaded (5xx, 429). The same request may work later;
- bad response: any other httpx request error (too many redirects,
  broken compression). Retrying won't help.

Each client passes its own error classes, so only domain errors leave it.
"""

from collections.abc import Awaitable, Callable

import httpx


def _no_detail(response: httpx.Response) -> str:
    return ""


async def send(
    request: Callable[[], Awaitable[httpx.Response]],
    *,
    what: str,
    unavailable: type[Exception],
    bad_response: type[Exception],
    detail: Callable[[httpx.Response], str] = _no_detail,
) -> httpx.Response:
    """Await the request and return the response unless it failed or the server is unavailable.

    `what` names the request in error messages. It must not contain secrets.
    `detail` can add the server's own error message to the "unavailable" error.
    """
    try:
        response = await request()
    except httpx.TransportError as error:
        raise unavailable(f"{what} failed: {type(error).__name__}") from error
    except httpx.RequestError as error:
        raise bad_response(f"{what} failed: {type(error).__name__}") from error
    if (
        response.is_server_error
        or response.status_code == httpx.codes.TOO_MANY_REQUESTS
    ):
        raise unavailable(f"{what} returned {response.status_code}{detail(response)}")
    return response
