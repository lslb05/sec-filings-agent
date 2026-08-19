# Decisões

Registre somente decisões que alterem custo de mudança futuro.

## Modelo

### AAAA-MM-DD — Título

- **Contexto:** qual restrição ou problema exigiu decisão.
- **Decisão:** o caminho escolhido.
- **Alternativas:** opções relevantes descartadas.
- **Consequências:** ganhos, custos e gatilho para revisar.

### 2026-08-18 — Manter `CLAUDE.md` e `AGENTS.md` no repositório público

- **Contexto:** os dois arquivos declaram que o repositório é construído com
  apoio de agentes. A alternativa era ignorá-los no git para que o repositório
  público não revelasse o fluxo de trabalho.
- **Decisão:** manter os dois versionados e públicos.
- **Alternativas:** ignorar `AGENTS.md` no `.gitignore`; mantê-lo apenas local.
  Ambas quebram a delegação ao Codex, que lê esse arquivo do repositório — o
  custo é funcional e imediato, o ganho é cosmético.
- **Consequências:** o repositório declara o método em vez de escondê-lo, o que
  também é verificável por quem lê. Rever se algum destino exigir o contrário.

### 2026-08-19 — Extração do Item 1A: três versões até generalizar

- **Contexto:** "Item 1A" aparece várias vezes num 10-K — sumário,
  cross-reference narrativa, cabeçalho real — e a primeira heurística
  ("a ocorrência com mais texto até o próximo marcador de item") quebrou
  contra a 10-K real da Apple de duas formas diferentes antes de generalizar:
  1. Uma cross-reference dentro do MD&A (que vem *depois* do Item 1A/1B/2 de
     verdade no documento) não tinha nenhum "Item 1B"/"Item 2" depois dela —
     o "resto do documento inteiro" virava candidato e vencia por tamanho.
  2. Corrigido isso, uma cross-reference *no início* do documento (antes do
     sumário) tinha o Item 1B real muito depois dela no texto — o span
     esticava por cima do sumário inteiro e da seção real, ainda vencendo.
  3. Corrigido para exigir "Risk Factors" logo depois de "Item 1A" no
     marcador de início (cross-reference narrativa nunca tem essa colocação
     exata), a Microsoft quebrou de um jeito novo: o HTML deles quebra a
     palavra "RISK" em "RIS K" no meio (artefato de renderização), e o
     cabeçalho real repete "PART I Item 1A" como header de página em toda
     página da seção — dezenas de ocorrências de "Item 1A" sem "Risk
     Factors" adjacente, que já não atrapalhavam mais porque não batem o
     marcador de início.
- **Decisão:** marcador de início = `item\s*1a\.?\s*ris\s?k\s*factors`
  (tolera o "RIS K" quebrado); candidato só é aceito se tiver um marcador de
  fim (`Item 1B`/`Item 2`) *encontrado de fato* — nunca "resto do documento"
  como fallback; entre os candidatos restantes, vence o de maior span.
  Validado contra 10-K real da Apple, Microsoft e Tesla — três formatos de
  HTML diferentes, todos corretos no fim.
- **Alternativas:** parsing do HTML original (não do texto já achatado) pra
  usar estrutura de heading/negrito como sinal — mais robusto em teoria, mas
  cada emissor usa HTML de tabela/div diferente pra formatar o mesmo
  documento; o sinal textual ("Item 1A. Risk Factors" colado) generalizou
  melhor na prática do que tentar usar formatação, que é exatamente o que
  varia mais entre 10-Ks de empresas diferentes.
- **Consequências:** a heurística é textual, não estrutural — um filer com
  formatação atípica ainda pode quebrá-la, e o comportamento nesse caso é
  falhar com `SecaoNaoEncontrada` (documentado como limitação), não devolver
  texto errado silenciosamente. Rever se um filer real quebrar de novo — os
  três casos documentados aqui são o histórico real de bugs, não hipótese.
