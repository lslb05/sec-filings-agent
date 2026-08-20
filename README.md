# agente-filings-sec

Agente LangGraph que compara o "Item 1A Risk Factors" de dois 10-Ks da mesma
empresa e lista o que mudou — cada mudança citando um trecho que precisa
aparecer, literalmente, no texto de origem.

## O problema

Comparar como o risk factors de uma empresa mudou de um 10-K pro outro é
trabalho manual de analista: ler duas seções longas e achar o que é novo,
removido ou alterado. Um agente que faz isso rápido não vale nada se
inventar mudança que não está no texto — então a citação de cada mudança é
conferida por correspondência literal contra o filing de origem antes de
sair na resposta final. Não existe "gabarito público" pra RAG sobre filing;
o grounding É a validação.

## Resultado

```console
$ uv run python -m agente_filings_sec comparar --ticker AAPL --ano-antigo 2023 --ano-novo 2024
tipo,filing,resumo,citacao
...
```

Não rodei esse comando de ponta a ponta com uma chave de verdade — este
ambiente de desenvolvimento não tem `ANTHROPIC_API_KEY` nem `OPENAI_API_KEY`
(ver Limitações). O que **foi** validado com dado real: busca no EDGAR e
extração do Item 1A contra 10-Ks de verdade da Apple, Microsoft e Tesla — as
três formatações diferentes de HTML quebraram a heurística de extração em
algum momento do desenvolvimento, e as correções ficaram documentadas em
`docs/decisions.md` porque valem a pena entender, não só corrigir.

## Problema e escopo

- **Usuário:** eu, e quem revisa o portfólio avaliando fluência com
  LLM/LangGraph.
- **Decisão:** lista de mudanças (novo/removido/alterado) entre o Item 1A de
  dois 10-Ks, cada uma com citação verificada contra o texto fonte.
- **Entrada:** SEC EDGAR — `data.sec.gov/submissions` e
  `www.sec.gov/files/company_tickers.json` (mapa ticker→CIK) e
  `sec.gov/Archives` (documento). Sem credencial, só `User-Agent` descritivo.
- **Fora de escopo:** mais de 2 filings por vez, seção além do Item 1A,
  vetorização/embedding, UI, observabilidade de custo de LLM em produção.

## Arquitetura

```
                    ┌─────────────────────┐
                    │ buscar_filing_antigo│
                    └──────────┬───────────┘
                               ▼
                    ┌─────────────────────┐
                    │ buscar_filing_novo  │
                    └──────────┬───────────┘
                               ▼
                    ┌─────────────────────┐
              ┌────▶│      comparar       │  chama o LLM (tool-calling)
              │     └──────────┬───────────┘
              │                ▼
              │     ┌─────────────────────┐
              │     │ verificar_citacoes  │  determinístico, sem LLM
              │     └──────────┬───────────┘
              │                ▼
      citação inválida    citação válida
      e tentativa < 3          │
              └────────────────┴──▶ fim
```

Três decisões que valem explicação:

**Tool-calling em vez de JSON em texto livre.** Tanto a Anthropic quanto a
OpenAI validam a forma da resposta contra um schema antes de devolver — não
sobra "o modelo esqueceu uma vírgula" pra tratar aqui. O conteúdo ainda é
revalidado por Pydantic, porque vir estruturado da API não dispensa validar
numa fronteira externa.

**Provedor de LLM é escolha de configuração, não de código.** `ClienteLLM` é
um `Protocol` com um único método (`comparar`); `ClienteAnthropic` e
`ClienteOpenAI` implementam o mesmo contrato contra APIs de tool-calling
diferentes, e `construir_cliente()` escolhe qual instanciar a partir de
`AGENTE_FILINGS_SEC_PROVEDOR_LLM`. `grafo.py` e `cli.py` só conhecem o
`Protocol` — trocar de provedor não muda uma linha deles.

**A aresta condicional é o que separa isto de uma função com um `if`.**
`verificar_citacoes` não chama o LLM — é substring determinística. Se uma
citação não bate no texto de origem, o grafo volta pro nó `comparar` com o
feedback específico do que falhou, até 3 tentativas. Testado de verdade
(`tests/test_grafo.py`): um LLM falso que erra na primeira tentativa e
acerta na segunda, provando que o loop e o feedback funcionam.

**A extração do Item 1A precisou de duas correções depois do design
inicial** — ver a próxima seção e `docs/decisions.md`. Isso não é um detalhe
de rodapé: é o risco técnico real deste projeto, mais do que o LLM em si.

## Executar localmente

Requisitos: Python 3.12, `uv`, e uma chave da Anthropic **ou** da OpenAI.

```bash
uv sync
cp .env.example .env      # preencha a chave do provedor escolhido
uv run python -m agente_filings_sec comparar --ticker AAPL --ano-antigo 2023 --ano-novo 2024
```

`AGENTE_FILINGS_SEC_PROVEDOR_LLM` escolhe o provedor (`anthropic`, padrão, ou
`openai`) — só a chave desse provedor precisa estar preenchida no `.env`.
Sem ela, o comando orienta e sai com código 2. Se o filing não for encontrado
ou a extração do Item 1A falhar, sai com código 2 também, com a mensagem
específica — nunca inventa resposta.

## Qualidade

```bash
uv run python scripts/check.py
```

O check executa formatação, lint, tipos e testes com cobertura. Nenhum teste
chama a API da Anthropic, da OpenAI nem a SEC de verdade — o cliente LLM e o
cliente HTTP são injetados, e os testes usam versões falsas/mockadas.

## Estrutura

```text
src/agente_filings_sec/
    fontes/edgar.py    ticker→CIK, lista de filings, download — sem credencial
    extrator.py         heurística de extração do Item 1A (o risco técnico real)
    citacoes.py          verificação determinística de citação
    llm.py                clientes Anthropic e OpenAI via tool-calling, interface injetável
    grafo.py              o grafo LangGraph: busca, compara, verifica, repete
    cli.py                 coordenação
```

## Limitações

- **Nunca validado contra a API da Anthropic nem da OpenAI de verdade.**
  Este ambiente de desenvolvimento não tem `ANTHROPIC_API_KEY` nem
  `OPENAI_API_KEY`. `fontes/edgar.py` e `extrator.py` foram validados contra
  filings reais (AAPL, MSFT, TSLA); o nó `comparar` e o loop de re-tentativa
  só foram testados com um LLM falso determinístico.
- A heurística de extração do Item 1A foi corrigida duas vezes durante o
  desenvolvimento contra três formatos reais diferentes — não há garantia de
  que generaliza para todo filer. Um 10-K com formatação atípica pode
  quebrá-la de novo; o comportamento nesse caso é falhar com
  `SecaoNaoEncontrada`, não devolver texto errado.
- Limite de 3 tentativas de correção de citação; se todas falharem, a saída
  sai com um aviso e as mudanças não verificadas continuam na lista — o
  chamador decide se confia nelas.

## Licença

MIT. Dados de terceiros mantêm suas próprias licenças e termos de uso.
