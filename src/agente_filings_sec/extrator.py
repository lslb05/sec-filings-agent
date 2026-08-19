"""Extração da seção Item 1A (Risk Factors) do texto de um 10-K.

O marcador "Item 1A" sozinho aparece várias vezes num 10-K real: no sumário,
em cross-references narrativas ("...discutido no Item 1A deste 10-K sob o
título 'Risk Factors'..."), e no cabeçalho real da seção. Duas versões
anteriores desta heurística ("ocorrência com mais texto até o próximo
marcador de item") quebraram contra uma 10-K real da Apple — uma
cross-reference dentro do MD&A não tinha nenhum marcador de fim depois dela
(virando "resto do documento"); outra cross-reference, bem no início do
documento, tinha o Item 1B real muito depois, criando um span enorme que
incluía o sumário inteiro e a seção real junto.

A correção: exigir "Risk Factors" logo depois de "Item 1A" no marcador de
início. Cross-reference narrativa nunca tem essa colocação exata — só o
sumário ("Item 1A. Risk Factors  5") e o cabeçalho real têm. Entre esses
dois, o de maior span até o próximo item é o real (o do sumário é curto).
"""

import re

from bs4 import BeautifulSoup

_MARCADOR_INICIO = re.compile(r"item\s*1a\.?\s*ris\s?k\s*factors", re.IGNORECASE)
_MARCADORES_FIM = re.compile(r"item\s*1b\b|item\s*2\b", re.IGNORECASE)

_TAMANHO_MINIMO = 500
_TAMANHO_MAXIMO = 100_000


class SecaoNaoEncontrada(Exception):
    """Nenhuma ocorrência de "Item 1A" tem texto suficiente pra ser a seção real."""


def html_para_texto(html: str) -> str:
    """HTML do filing, colapsado em texto plano com espaço em branco normalizado."""
    texto = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    return re.sub(r"\s+", " ", texto).strip()


def extrair_item_1a(texto_plano: str) -> str:
    """`texto_plano` já deve vir de `html_para_texto`."""
    inicios = [m.end() for m in _MARCADOR_INICIO.finditer(texto_plano)]
    if not inicios:
        raise SecaoNaoEncontrada("nenhuma ocorrência de 'Item 1A' no documento")

    candidatos = []
    for inicio in inicios:
        fim_match = _MARCADORES_FIM.search(texto_plano, inicio)
        if fim_match is None:
            continue  # sem marcador de fim, não é a seção real — ver docstring
        candidatos.append((fim_match.start() - inicio, inicio, fim_match.start()))

    if not candidatos:
        raise SecaoNaoEncontrada(
            "nenhuma ocorrência de 'Item 1A' tem um marcador de fim depois dela"
        )

    tamanho, inicio, fim = max(candidatos)
    if tamanho < _TAMANHO_MINIMO:
        raise SecaoNaoEncontrada(
            "nenhuma ocorrência de 'Item 1A' tem texto suficiente pra ser a seção real"
        )

    return texto_plano[inicio:fim].strip()[:_TAMANHO_MAXIMO]
