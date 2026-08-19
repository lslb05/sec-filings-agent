"""Interface de linha de comando. A lógica vive no pacote; aqui só coordena."""

import argparse
import sys

import httpx

from agente_filings_sec.config import Settings
from agente_filings_sec.extrator import SecaoNaoEncontrada
from agente_filings_sec.fontes.edgar import FilingNaoEncontrado
from agente_filings_sec.grafo import construir_grafo, estado_inicial
from agente_filings_sec.llm import ClienteAnthropic


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    principal = argparse.ArgumentParser(prog="agente-filings-sec")
    comandos = principal.add_subparsers(dest="comando", required=True)

    comparar = comandos.add_parser(
        "comparar", help="mudanças no Item 1A entre dois 10-Ks do mesmo ticker"
    )
    comparar.add_argument("--ticker", required=True)
    comparar.add_argument("--ano-antigo", required=True, type=int)
    comparar.add_argument("--ano-novo", required=True, type=int)

    return principal.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argumentos = _argumentos(argv)
    config = Settings()

    if not config.anthropic_api_key:
        print(
            "defina AGENTE_FILINGS_SEC_ANTHROPIC_API_KEY (chave da Anthropic)",
            file=sys.stderr,
        )
        return 2

    cliente_llm = ClienteAnthropic(chave_api=config.anthropic_api_key)

    with httpx.Client(headers={"User-Agent": config.edgar_user_agent}) as cliente_http:
        grafo = construir_grafo(cliente_llm=cliente_llm, cliente_http=cliente_http)
        estado = estado_inicial(
            ticker=argumentos.ticker,
            ano_antigo=argumentos.ano_antigo,
            ano_novo=argumentos.ano_novo,
        )
        try:
            resultado = grafo.invoke(estado)
        except FilingNaoEncontrado as erro:
            print(f"filing não encontrado: {erro}", file=sys.stderr)
            return 2
        except SecaoNaoEncontrada as erro:
            print(f"não foi possível extrair o Item 1A: {erro}", file=sys.stderr)
            return 2

    citacoes_invalidas = resultado["citacoes_invalidas"]
    if citacoes_invalidas:
        print(
            f"aviso: {len(citacoes_invalidas)} citação(ões) não verificada(s) "
            f"após {resultado['tentativa']} tentativa(s)",
            file=sys.stderr,
        )

    print("tipo,filing,resumo,citacao")
    for mudanca in resultado["mudancas"]:
        resumo = mudanca["resumo"].replace('"', "'")
        citacao = mudanca["citacao"].replace('"', "'")
        print(f'{mudanca["tipo"]},{mudanca["filing"]},"{resumo}","{citacao}"')
    return 0
