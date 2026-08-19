"""Acesso ao SEC EDGAR: ticker→CIK, lista de filings e download do documento.

Nenhuma credencial — a única exigência da SEC é um User-Agent descritivo
identificando quem está acessando. Sem ele, a SEC responde 403.
"""

import httpx

_MAPA_TICKERS = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSOES = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_ARQUIVO = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{documento}"

_TIMEOUT_S = 30.0
_TENTATIVAS = 3


class FilingNaoEncontrado(Exception):
    """Ticker sem CIK conhecido, ou sem 10-K publicado no ano pedido."""


def buscar_cik(ticker: str, *, cliente: httpx.Client) -> int:
    resposta = _obter(_MAPA_TICKERS, cliente)
    for entrada in resposta.json().values():
        if entrada["ticker"].upper() == ticker.upper():
            return int(entrada["cik_str"])
    raise FilingNaoEncontrado(f"ticker '{ticker}' não encontrado no mapa da SEC")


def buscar_10k(ticker: str, ano: int, *, cliente: httpx.Client) -> str:
    """Devolve o HTML do 10-K de `ticker` cuja `filingDate` cai em `ano`."""
    cik = buscar_cik(ticker, cliente=cliente)
    resposta = _obter(_SUBMISSOES.format(cik=cik), cliente)
    filings = resposta.json()["filings"]["recent"]

    for forma, data, accession, documento in zip(
        filings["form"],
        filings["filingDate"],
        filings["accessionNumber"],
        filings["primaryDocument"],
        strict=True,
    ):
        if forma == "10-K" and data.startswith(str(ano)):
            url = _ARQUIVO.format(
                cik=cik, accession=accession.replace("-", ""), documento=documento
            )
            return _obter(url, cliente).text

    raise FilingNaoEncontrado(f"nenhum 10-K de '{ticker}' arquivado em {ano}")


def _obter(url: str, cliente: httpx.Client) -> httpx.Response:
    ultima: Exception | None = None
    for _tentativa in range(_TENTATIVAS):
        try:
            resposta = cliente.get(url, timeout=_TIMEOUT_S)
        except httpx.TransportError as erro:
            ultima = erro
        else:
            if resposta.status_code < 400:
                return resposta
            # 4xx é erro nosso (ticker/CIK/URL errados) — repetir não conserta.
            if resposta.status_code < 500:
                raise FilingNaoEncontrado(
                    f"SEC respondeu {resposta.status_code} para {url}"
                )
            ultima = FilingNaoEncontrado(f"SEC respondeu {resposta.status_code}")
    raise FilingNaoEncontrado(
        f"SEC não respondeu após {_TENTATIVAS} tentativas"
    ) from ultima
