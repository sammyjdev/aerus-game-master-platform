# TODO — Narrador hospedado (evoluções pós-integração)

> O narrador hospedado (frontier + RAG + guardrail) já está **integrado e funcional**
> (`HOSTED_NARRATOR_ENABLED=true`). Este TODO lista as evoluções deferidas — produto,
> não pendência de release. Contexto completo: `aerum-narrator/DECISAO_NARRADOR.md`.

Status: 🔴 não iniciado · 🟡 em progresso · 🟢 feito

---

## 1. 🔴 Streaming otimista do narrador hospedado

**Hoje:** `hosted_narrator.narrate()` gera **não-streamado**, valida no guardrail e só
então o `game_master` envia o texto inteiro (uma "chunk"). Há latência inicial e perde-se
o streaming token-a-token.

**Meta:** streaming ao vivo (token-a-token) sem abrir mão da garantia.

**Abordagem (escolher uma):**
- **A — Otimista puro:** streamar a 1ª tentativa ao vivo via `broadcast_stream`; validar
  *pós-hoc*; em falha, emitir sinal de correção + streamar a versão regenerada (exige o
  frontend suportar *replace* da narração). Melhor UX, mais trabalho no front.
- **B — Validado-então-chunked (pragmático):** manter a validação antes, mas streamar o
  texto validado em pedaços com pequenos delays (sensação de streaming, garantia intacta).
  Menos "vivo", zero risco de mostrar conteúdo rejeitado.

**Arquivos:** `backend/src/game_master.py` (branch `is_hosted_narrator`, ~linha 528),
`backend/src/connection_manager.py` (`broadcast_stream`), `backend/src/hosted_narrator.py`.

**Aceite:** narração aparece progressivamente no front; nenhuma saída não-conforme exibida
de forma definitiva; métrica de regeneração logada.

---

## 2. 🔴 Fluxo dado → narração (a sacada do teste cego)

**Hoje:** narra-se primeiro e o **extractor (Ollama) parseia o dado da prosa depois**
(`_extract_game_state_b1`). O narrador pode "vazar" o resultado antes da rolagem.

**Meta:** num RPG, **resolver/solicitar a rolagem ANTES** e o narrador descreve a
**consequência** do resultado já conhecido.

**Abordagem:**
1. Classificar se a ação exige rolagem e qual (ataque / perícia / save) — heurística ou
   um classificador leve (Ollama).
2. Engine **rola o dado** (determinístico) ou pede a rolagem ao jogador (já há
   `DiceRollRequestBody`/`DiceRollResolveBody` em `models.py`).
3. Injetar o **resultado da rolagem** no prompt do narrador → ele narra o desfecho conhecido.

**Arquivos:** `backend/src/game_master.py` (turn loop / `process_batch`),
`backend/src/models.py` (contratos de dado já existem), `backend/src/hosted_narrator.py`
(receber o resultado da rolagem no prompt).

**Risco:** mudança no turn-loop; **validar com o jogo rodando** (E2E). Maior item da lista.

---

## 3. 🔴 RAG semântico mais forte

**Hoje:** `retrieve_narration_examples` recupera por similaridade do *texto da ação* +
filtro opcional de `scene_type`, com o embedding default do ChromaDB.

**Meta:** recuperação por **situação** (ação + contexto), embedding melhor
(`bge-m3` via Ollama, já instalado), e ponderar por `scene_type`/`tension`.

**Arquivos:** `backend/src/vector_store.py` (`_get_narration_collection`, custom
`embedding_function`; `ingest/retrieve_narration_examples`).

---

## 4. 🔴 Afinar o guardrail

- Completar o **dicionário de verbos de NPC** (regex deu falso-positivo: "abaixa" faltava).
- Melhorar a **heurística de 2ª pessoa** (hoje: nome-sujeito sem "você" → flag).
- Se `scene_type` ficar disponível, usar o **cap por cena** (hoje há um teto global soft = 6).

**Arquivos:** `backend/src/hosted_narrator.py` (`validate`, `_FORBIDDEN`).

---

## 5. 🔴 Caching de prompt (custo)

Estruturar o prompt com o **prefixo estático primeiro** (kernel + exemplos RAG) para
maximizar cache-hit. DeepSeek: automático. Anthropic-direto: marcar `cache_control`
(ephemeral) no fim do bloco estático. Reduz ~pela metade o custo/turno.

**Arquivos:** `backend/src/hosted_narrator.py` (`build_messages`); `.env` (base_url/key
Anthropic-direto se for o caso).

---

## 6. 🔴 Observabilidade

Logar por turno: status do guardrail (pass/regen/best_effort), nº de chamadas, latência.
Amostragem periódica (humano) para deriva de voz (o subjetivo não é garantível por código).

---

### Referências
- Decisão/arquitetura completa: `aerum-narrator/DECISAO_NARRADOR.md`
- Material do artigo: `docs/ARTIGO_LINKEDIN_CORE.md`
- Gap analysis do narrador: `docs/GAP_ANALYSIS_NARRATOR.md`
