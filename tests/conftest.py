from collections.abc import Callable

import httpx
import pytest

CriaClienteMock = Callable[[dict[str, httpx.Response]], httpx.Client]


@pytest.fixture
def criar_cliente_mock() -> CriaClienteMock:
    """Cliente httpx cujas respostas são escolhidas pela URL exata pedida."""

    def criar(respostas: dict[str, httpx.Response]) -> httpx.Client:
        def responder(requisicao: httpx.Request) -> httpx.Response:
            url = str(requisicao.url)
            if url not in respostas:
                raise AssertionError(f"URL não mockada: {url}")
            return respostas[url]

        return httpx.Client(transport=httpx.MockTransport(responder))

    return criar
