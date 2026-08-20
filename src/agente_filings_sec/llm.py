"""Cliente LLM: compara duas seções de risk factors via tool-calling.

Tool-calling em vez de pedir JSON em texto livre: tanto a Anthropic quanto a
OpenAI validam a forma da resposta contra um schema antes de devolver, então
não há "o modelo esqueceu uma vírgula" pra tratar aqui — só o conteúdo,
validado de novo por Pydantic (fronteira externa, mesmo vindo já
estruturado). Os dois provedores implementam o mesmo `ClienteLLM`; grafo.py
e cli.py não sabem qual é o de verdade.
"""

import json
from typing import Any, Literal, Protocol

import anthropic
import openai
from pydantic import BaseModel

_MODELO_PADRAO_ANTHROPIC = "claude-sonnet-4-5"
_MODELO_PADRAO_OPENAI = "gpt-5.4"
_MAX_TOKENS = 4096

_FERRAMENTA: dict[str, Any] = {
    "name": "registrar_mudancas",
    "description": (
        "Registra as mudanças encontradas entre as duas versões da seção de "
        "risk factors de um 10-K."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "mudancas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tipo": {
                            "type": "string",
                            "enum": ["novo", "removido", "alterado"],
                        },
                        "resumo": {
                            "type": "string",
                            "description": "Uma frase explicando a mudança.",
                        },
                        "citacao": {
                            "type": "string",
                            "description": (
                                "Trecho copiado EXATAMENTE do texto de origem "
                                "que evidencia a mudança."
                            ),
                        },
                        "filing": {
                            "type": "string",
                            "enum": ["antigo", "novo"],
                            "description": "De qual filing a citação foi copiada.",
                        },
                    },
                    "required": ["tipo", "resumo", "citacao", "filing"],
                },
            },
        },
        "required": ["mudancas"],
    },
}


class MudancaBruta(BaseModel):
    tipo: Literal["novo", "removido", "alterado"]
    resumo: str
    citacao: str
    filing: Literal["antigo", "novo"]


class _RespostaFerramenta(BaseModel):
    mudancas: list[MudancaBruta]


class ClienteLLM(Protocol):
    """Interface injetável — testes usam um cliente falso, sem chamar a API."""

    def comparar(
        self, *, texto_antigo: str, texto_novo: str, feedback: list[str]
    ) -> list[MudancaBruta]: ...


class ClienteAnthropic:
    def __init__(
        self, *, chave_api: str, modelo: str = _MODELO_PADRAO_ANTHROPIC
    ) -> None:
        self._cliente = anthropic.Anthropic(api_key=chave_api)
        self._modelo = modelo

    def comparar(
        self, *, texto_antigo: str, texto_novo: str, feedback: list[str]
    ) -> list[MudancaBruta]:
        # Os tipos de tool-use da SDK da Anthropic são profundos demais pra
        # valer a pena replicar aqui; o schema real é validado em runtime
        # pela própria API, e a resposta é revalidada por Pydantic abaixo.
        resposta = self._cliente.messages.create(
            model=self._modelo,
            max_tokens=_MAX_TOKENS,
            tools=[_FERRAMENTA],
            tool_choice={"type": "tool", "name": "registrar_mudancas"},
            messages=[
                {
                    "role": "user",
                    "content": _montar_prompt(texto_antigo, texto_novo, feedback),
                }
            ],
        )  # type: ignore[call-overload]
        bloco = next(b for b in resposta.content if b.type == "tool_use")
        return _RespostaFerramenta.model_validate(bloco.input).mudancas


class ClienteOpenAI:
    """Mesmo contrato do ClienteAnthropic, via function-calling da OpenAI.

    A OpenAI usa `parameters` em vez de `input_schema` e devolve os
    argumentos da função como string JSON, não objeto — daí o `json.loads`
    antes da revalidação por Pydantic, que o cliente Anthropic não precisa.
    """

    def __init__(self, *, chave_api: str, modelo: str = _MODELO_PADRAO_OPENAI) -> None:
        self._cliente = openai.OpenAI(api_key=chave_api)
        self._modelo = modelo

    def comparar(
        self, *, texto_antigo: str, texto_novo: str, feedback: list[str]
    ) -> list[MudancaBruta]:
        resposta = self._cliente.chat.completions.create(
            model=self._modelo,
            max_completion_tokens=_MAX_TOKENS,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": _FERRAMENTA["name"],
                        "description": _FERRAMENTA["description"],
                        "parameters": _FERRAMENTA["input_schema"],
                    },
                }
            ],
            tool_choice={
                "type": "function",
                "function": {"name": "registrar_mudancas"},
            },
            messages=[
                {
                    "role": "user",
                    "content": _montar_prompt(texto_antigo, texto_novo, feedback),
                }
            ],
        )
        chamada = resposta.choices[0].message.tool_calls
        if not chamada or chamada[0].type != "function":
            raise ValueError("a OpenAI respondeu sem chamar registrar_mudancas")
        argumentos = json.loads(chamada[0].function.arguments)
        return _RespostaFerramenta.model_validate(argumentos).mudancas


def construir_cliente(
    *,
    provedor: Literal["anthropic", "openai"],
    anthropic_api_key: str | None,
    anthropic_modelo: str | None,
    openai_api_key: str | None,
    openai_modelo: str | None,
) -> ClienteLLM:
    """Monta o cliente do provedor escolhido, ou levanta se faltar a chave."""
    if provedor == "anthropic":
        if not anthropic_api_key:
            raise ValueError("AGENTE_FILINGS_SEC_ANTHROPIC_API_KEY não definida")
        if anthropic_modelo:
            return ClienteAnthropic(
                chave_api=anthropic_api_key, modelo=anthropic_modelo
            )
        return ClienteAnthropic(chave_api=anthropic_api_key)
    if not openai_api_key:
        raise ValueError("AGENTE_FILINGS_SEC_OPENAI_API_KEY não definida")
    if openai_modelo:
        return ClienteOpenAI(chave_api=openai_api_key, modelo=openai_modelo)
    return ClienteOpenAI(chave_api=openai_api_key)


def _montar_prompt(texto_antigo: str, texto_novo: str, feedback: list[str]) -> str:
    partes = [
        "Compare as duas versões abaixo da seção 'Item 1A Risk Factors' de um "
        "10-K da mesma empresa, em anos diferentes. Liste cada risco que foi "
        "adicionado, removido ou alterado de forma relevante — ignore mudança "
        "puramente de redação sem mudança de conteúdo.\n\n"
        "Para cada mudança, copie um trecho curto (uma frase) EXATAMENTE como "
        "aparece no texto de origem correspondente — a citação será conferida "
        "por correspondência literal contra o texto original, então não "
        "parafraseie.\n\n",
        f"FILING ANTIGO:\n{texto_antigo}\n\n",
        f"FILING NOVO:\n{texto_novo}\n",
    ]
    if feedback:
        partes.append(
            "\n\nNa tentativa anterior, estas citações não foram encontradas "
            "literalmente no texto de origem — corrija-as, copiando o texto "
            "exato desta vez:\n" + "\n".join(f"- {item}" for item in feedback)
        )
    return "".join(partes)
