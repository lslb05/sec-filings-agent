# Contrato do projeto — Agente Filings Sec

Leia o `CLAUDE.md` global e use este arquivo para o que é específico deste
repositório.

## Resultado do produto

- **Problema:** comparar como o "Item 1A Risk Factors" de uma empresa mudou
  de um 10-K pro outro é trabalho manual de analista. Um agente que faz isso
  e cita a fonte prova RAG com grounding verificável, não resumo que pode
  estar inventando.
- **Usuário:** eu, e quem revisa o portfólio avaliando fluência com
  LLM/LangGraph.
- **Saída verificável:** lista de mudanças (novo/removido/alterado) entre o
  Item 1A de dois 10-Ks da mesma empresa, cada item com citação curta que
  precisa aparecer literalmente no texto fonte correspondente.
- **Fonte de dados permitida:** SEC EDGAR — `data.sec.gov/submissions`
  (lista de filings por CIK) e `sec.gov/Archives` (documento do 10-K), sem
  credencial, só `User-Agent` descritivo.
- **Menor corte ponta a ponta:** CLI que recebe ticker + dois anos, roda o
  grafo LangGraph, imprime a lista de mudanças com citação e filing de
  origem.
- **Fora de escopo:** mais de 2 filings por vez, seção além do Item 1A,
  vetorização/embedding, UI, observabilidade de custo de LLM em produção.

Não implemente enquanto um `PREENCHER` que altere o design continuar em aberto.

## Comandos

```bash
uv sync
uv run python scripts/format.py
uv run python scripts/check.py
```

## Regras locais

- O pacote é `agente_filings_sec` e vive em `src/agente_filings_sec`.
- Notebook importa de `src/`; código de produção nunca importa notebook.
- Configuração vem de ambiente por `Settings`.
- Preserve dado bruto e metadados temporais quando houver ingestão.
- Atualize este arquivo quando uma decisão estrutural mudar.

## Estilo

Código público, lido por gente. A regra é contenção — a lista completa está em
`AGENTS.md`, seção "Style", e vale igual para mim e para o Codex.

- Comentário explica *por quê*, nunca *o quê*. Se parafraseia a linha abaixo,
  apague; se a linha precisa de paráfrase, renomeie a variável.
- Docstring só onde a assinatura não basta (unidade, fuso, efeito colateral,
  o que levanta). Helper privado de três linhas não leva.
- Teste afirma comportamento que pode quebrar, não constante. Cobertura é
  consequência de testar o que importa, nunca meta a inflar.
- Não capture exceção que não sabe tratar; não abstraia com um único chamador.

## Autoria dos commits

Autor e committer são um só: o dono do repositório. Nenhum `Co-Authored-By:`,
nenhum trailer de sessão, nenhuma menção a Claude, Codex ou ferramenta. Não
altere `user.name` nem `user.email`.

## Estado da sessão

- **Decidido:** primeiro corte entregue — grafo LangGraph (busca os dois
  filings, compara via LLM com tool-calling, verifica citação
  deterministicamente, repete com feedback se alguma citação falhar, até 3
  tentativas). Extração do Item 1A validada contra 10-K real de AAPL, MSFT e
  TSLA depois de três correções (ver `docs/decisions.md`).
- **Decidido:** `ClienteLLM` é um `Protocol` de um método; `ClienteAnthropic`
  e `ClienteOpenAI` (`src/agente_filings_sec/llm.py`) implementam o mesmo
  contrato contra tool-calling da Anthropic e function-calling da OpenAI.
  `construir_cliente()` escolhe qual instanciar a partir de
  `AGENTE_FILINGS_SEC_PROVEDOR_LLM` (`anthropic` padrão, ou `openai`) — só a
  chave do provedor escolhido precisa estar definida. `grafo.py` e `cli.py`
  não conhecem qual concreto está por trás do `Protocol`.
- **Pendente:** nunca rodou contra a API da Anthropic nem da OpenAI de
  verdade — sem `ANTHROPIC_API_KEY` nem `OPENAI_API_KEY` neste ambiente. O
  nó `comparar` e o loop de re-tentativa só têm cobertura com LLM falso
  determinístico, para os dois provedores.
- **Próximo passo:** com uma chave real (de qualquer um dos dois
  provedores), rodar `comparar` de verdade contra um par de 10-Ks reais e
  conferir se as citações que o modelo produz passam na verificação na
  primeira tentativa ou se o loop de correção é realmente necessário na
  prática.

