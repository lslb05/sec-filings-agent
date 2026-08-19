"""Grafo LangGraph: busca os dois filings, compara, verifica citação, repete
se preciso.

O nó de comparação chama o LLM; o de verificação não chama — é puro Python
conferindo substring. É a aresta condicional entre os dois que faz o grafo
valer a pena sobre uma chamada de função só: se alguma citação não bate no
texto de origem, o estado volta pro nó de comparação com o feedback
específico do que falhou, até um limite de tentativas.
"""

from typing import Any, Literal, TypedDict

import httpx
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agente_filings_sec.citacoes import citacao_valida
from agente_filings_sec.extrator import extrair_item_1a, html_para_texto
from agente_filings_sec.fontes.edgar import buscar_10k
from agente_filings_sec.llm import ClienteLLM

LIMITE_TENTATIVAS = 3


class Mudanca(TypedDict):
    tipo: Literal["novo", "removido", "alterado"]
    resumo: str
    citacao: str
    filing: Literal["antigo", "novo"]


class Estado(TypedDict):
    ticker: str
    ano_antigo: int
    ano_novo: int
    texto_antigo: str
    texto_novo: str
    mudancas: list[Mudanca]
    tentativa: int
    citacoes_invalidas: list[str]


def estado_inicial(*, ticker: str, ano_antigo: int, ano_novo: int) -> Estado:
    return Estado(
        ticker=ticker,
        ano_antigo=ano_antigo,
        ano_novo=ano_novo,
        texto_antigo="",
        texto_novo="",
        mudancas=[],
        tentativa=0,
        citacoes_invalidas=[],
    )


def construir_grafo(
    *, cliente_llm: ClienteLLM, cliente_http: httpx.Client
) -> CompiledStateGraph[Estado, None, Estado, Estado]:
    def no_buscar_filing_antigo(estado: Estado) -> dict[str, Any]:
        html = buscar_10k(estado["ticker"], estado["ano_antigo"], cliente=cliente_http)
        return {"texto_antigo": extrair_item_1a(html_para_texto(html))}

    def no_buscar_filing_novo(estado: Estado) -> dict[str, Any]:
        html = buscar_10k(estado["ticker"], estado["ano_novo"], cliente=cliente_http)
        return {"texto_novo": extrair_item_1a(html_para_texto(html))}

    def no_comparar(estado: Estado) -> dict[str, Any]:
        mudancas_brutas = cliente_llm.comparar(
            texto_antigo=estado["texto_antigo"],
            texto_novo=estado["texto_novo"],
            feedback=estado["citacoes_invalidas"],
        )
        mudancas: list[Mudanca] = [
            Mudanca(tipo=m.tipo, resumo=m.resumo, citacao=m.citacao, filing=m.filing)
            for m in mudancas_brutas
        ]
        return {"mudancas": mudancas, "tentativa": estado["tentativa"] + 1}

    def no_verificar_citacoes(estado: Estado) -> dict[str, Any]:
        textos = {"antigo": estado["texto_antigo"], "novo": estado["texto_novo"]}
        invalidas = [
            mudanca["citacao"]
            for mudanca in estado["mudancas"]
            if not citacao_valida(mudanca["citacao"], textos[mudanca["filing"]])
        ]
        return {"citacoes_invalidas": invalidas}

    def decidir_apos_verificacao(estado: Estado) -> str:
        if not estado["citacoes_invalidas"]:
            return "fim"
        if estado["tentativa"] >= LIMITE_TENTATIVAS:
            return "fim"
        return "tentar_novamente"

    # As sobrecargas de add_node do LangGraph exigem inferência de tipo que
    # não fecha de forma limpa para nó que devolve atualização parcial do
    # estado (dict[str, Any]) em vez do TypedDict inteiro — comportamento
    # documentado do LangGraph, não erro real de tipo aqui.
    grafo = StateGraph(Estado)
    grafo.add_node("buscar_filing_antigo", no_buscar_filing_antigo)  # type: ignore[call-overload]
    grafo.add_node("buscar_filing_novo", no_buscar_filing_novo)  # type: ignore[call-overload]
    grafo.add_node("comparar", no_comparar)  # type: ignore[call-overload]
    grafo.add_node("verificar_citacoes", no_verificar_citacoes)  # type: ignore[call-overload]

    grafo.set_entry_point("buscar_filing_antigo")
    grafo.add_edge("buscar_filing_antigo", "buscar_filing_novo")
    grafo.add_edge("buscar_filing_novo", "comparar")
    grafo.add_edge("comparar", "verificar_citacoes")
    grafo.add_conditional_edges(
        "verificar_citacoes",
        decidir_apos_verificacao,
        {"tentar_novamente": "comparar", "fim": END},
    )
    return grafo.compile()
