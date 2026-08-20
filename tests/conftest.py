from collections.abc import Callable

import httpx
import pytest

MakeMockClient = Callable[[dict[str, httpx.Response]], httpx.Client]


@pytest.fixture
def make_mock_client() -> MakeMockClient:
    """An httpx client whose responses are picked by the exact URL requested."""

    def make(responses: dict[str, httpx.Response]) -> httpx.Client:
        def respond(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url not in responses:
                raise AssertionError(f"URL not mocked: {url}")
            return responses[url]

        return httpx.Client(transport=httpx.MockTransport(respond))

    return make
