"""Interface de linha de comando. A lógica vive no pacote; aqui só coordena."""

import argparse
import sys

import httpx

from agente_filings_sec.config import Settings
from agente_filings_sec.extrator import SecaoNaoEncontrada
from agente_filings_sec.fontes.edgar import FilingNaoEncontrado
from agente_filings_sec.grafo import construir_grafo, estado_inicial
from agente_filings_sec.llm import construir_cliente


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

    try:
        cliente_llm = construir_cliente(
            provedor=config.provedor_llm,
            anthropic_api_key=config.anthropic_api_key,
            anthropic_modelo=config.anthropic_modelo,
            openai_api_key=config.openai_api_key,
            openai_modelo=config.openai_modelo,
        )
    except ValueError as erro:
        print(
            f"{erro} (AGENTE_FILINGS_SEC_PROVEDOR_LLM={config.provedor_llm})",
            file=sys.stderr,
        )
        return 2

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
