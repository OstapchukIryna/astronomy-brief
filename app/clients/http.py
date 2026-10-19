"""Turn the outcome of an httpx request into a client's own errors.

All clients classify failures this way:
- unavailable: the request didn't get an answer (TransportError: timeout,
  connection error, broken connection) or the server is failing or
  overloaded (5xx, 429).
- rate limited: 429, if the client passes its own error for it.
- bad response: any other request error (too many redirects,
  broken compression).
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
    rate_limited: type[Exception] | None = None,
    detail: Callable[[httpx.Response], str] = _no_detail,
) -> httpx.Response:
    """Await the request and return the response unless it failed or the server is unavailable.

    `what` names the request in error messages. Must not contain secrets.
    `detail` can add the server's own error message to the "unavailable" error.
    `rate_limited` is raised on 429.
    """
    try:
        response = await request()
    except httpx.TransportError as error:
        raise unavailable(f"{what} failed: {type(error).__name__}") from error
    except httpx.RequestError as error:
        raise bad_response(f"{what} failed: {type(error).__name__}") from error
    if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
        error = rate_limited or unavailable
    elif response.is_server_error:
        error = unavailable
    else:
        return response
    raise error(f"{what} returned {response.status_code}{detail(response)}")
