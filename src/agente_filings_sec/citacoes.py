"""Verificação determinística de citação — a peça que faz o grounding valer.

Nenhuma chamada de LLM aqui. Uma citação só é válida se aparecer, literalmente
(depois de normalizar espaço em branco e caixa), no texto de origem. É essa
função — não a boa vontade do modelo — que garante que uma mudança relatada
não foi inventada.
"""

import re


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip().lower()


def citacao_valida(citacao: str, texto_fonte: str) -> bool:
    if not citacao.strip():
        return False
    return _normalizar(citacao) in _normalizar(texto_fonte)
