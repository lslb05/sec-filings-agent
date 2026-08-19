"""Cliente LLM: compara duas seções de risk factors via tool-calling.

Tool-calling em vez de pedir JSON em texto livre: a Anthropic API valida a
forma da resposta contra o schema antes de devolver, então não há
"o modelo esqueceu uma vírgula" pra tratar aqui — só o conteúdo, validado de
novo por Pydantic (fronteira externa, mesmo vindo já estruturado).
"""

from typing import Any, Literal, Protocol

import anthropic
from pydantic import BaseModel

_MODELO_PADRAO = "claude-sonnet-4-5"
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
    def __init__(self, *, chave_api: str, modelo: str = _MODELO_PADRAO) -> None:
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
