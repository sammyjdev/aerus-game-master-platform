# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

Aerus é um RPG narrativo cooperativo multiplayer com backend em FastAPI (WebSocket + HTTP) e frontend em React.

- Backend: orquestração de turnos, persistência de estado, contexto para LLM, eventos de jogo.
- Frontend: experiência do jogador, streaming narrativo, sincronização de estado, UI de combate e narrativa.

## Comandos úteis

### Backend

```bash
# Iniciar servidor com hot-reload
cd backend && .venv/Scripts/uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env

# Rodar todos os testes unitários
cd backend && .venv/Scripts/python -m pytest tests/ -v

# Rodar um teste específico
cd backend && .venv/Scripts/python -m pytest tests/test_state_manager.py -v

# Rodar testes E2E (Playwright — requer servidor ativo)
cd backend && .venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -v -s
```

### Frontend

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
npm run build
npm test          # Vitest (unit tests)
```

### Makefile (atalhos)

```bash
make setup        # Cria venv + instala dependências
make full-dev     # Backend + frontend em paralelo
make test         # Roda pytest
make clean        # Remove aerus.db, chroma_db, caches
```

## Arquitetura do backend

### Camadas

| Camada | Local | Responsabilidade |
|--------|-------|-----------------|
| API/Transport | `src/main.py` | Rotas HTTP e WebSocket, middleware, lifespan |
| Application | `src/application/` | Orquestração de casos de uso (ex: billing) |
| Infrastructure | `src/infrastructure/` | Config loader, integrações externas |
| Core (legado em migração) | `src/*.py` | game_master, state_manager, context_builder… |

**Regras rígidas:**
- Zero lógica de negócio em `main.py`
- SQL exclusivamente em `state_manager.py`
- ChromaDB exclusivamente em `vector_store.py`
- Preservar compatibilidade de imports públicos ao migrar módulos para `application/` ou `infrastructure/`

### Módulos centrais

- **`game_master.py`** — orquestra turnos (batch de 3s), seleciona modelo por nível de tensão, faz parse de eventos.
- **`state_manager.py`** — 14 tabelas SQLite (WAL mode obrigatório), aplica deltas de estado, auto level-up.
- **`context_builder.py`** — 4 camadas de contexto (L0 kernel ~200 tok, L1 campanha ~170, L2 estado ~400, L3 histórico ~1500) + memória (~200) + lore retrieval (~800).
- **`billing_router.py`** e `application/billing/billing_router.py` — roteamento BYOK vs. admin key por tensão.
- **`vector_store.py`** — ingere bestiary.md + world.md (por seção) no ChromaDB no startup, busca semântica por lore e criatura.
- **`connection_manager.py`** — gerencia salas WebSocket, streaming token-a-token, heartbeat.

### Restrição de deploy

`fly.toml` define `max_machines = 1`. Sharding requer migração para PostgreSQL antes de escalar.

## Arquitetura do frontend

### Organização híbrida

- `pages/*` — composição de telas (LoginPage, CharacterCreationPage, GamePage)
- `features/game/` — entrypoints de domínio; páginas devem importar via `features/` quando disponível
- `components/*` — componentes por domínio (`character/`, `combat/`, `narrative/`, `screens/`, `ui/`)
- `store/gameStore.ts` — Zustand, única fonte de verdade do estado do jogo
- `hooks/useWebSocket.ts` — gerencia conexão WS e despacho de mensagens
- `api/http.ts` — wrappers de fetch para endpoints REST

## Lore e configuração

- `lore/` = fonte canônica autoral (`world.md`, `bestiary.md`)
- `backend/config/` = cópia operacional usada em runtime pelo servidor
- `backend/config/world_kernel.md` = resumo compacto (~200 tokens) do mundo, injetado como L0 static em toda chamada ao GM
- **Ao editar lore, sincronizar para `backend/config/` antes de validar comportamento em jogo**
- **Ao editar `world.md` ou qualquer `bestiary_tN.md`, deletar `backend/chroma_db/` para forçar re-ingestão no próximo startup**
- `backend/config/bestiary_t{1-5}.md` = bestiary dividido por tier (Tier 1-5). `bestiary.md` é apenas índice.
- `backend/config/campaign.yaml` controla: `max_players`, `darkness_level`, `permadeath`, seleção de modelos LLM, orçamento de tokens por camada, mecânicas (batch window, history turns, level cap)

## Variáveis de ambiente

Backend (`.env`): `OPENROUTER_API_KEY`, `FERNET_KEY`, `JWT_SECRET`, `OLLAMA_BASE_URL`, `CHROMA_DB_PATH`, `LOG_LEVEL`

Frontend (`.env.local`): `VITE_API_URL`

## Artefatos locais (não versionar)

`backend/.venv`, `backend/aerus.db`, `backend/chroma_db`, `frontend/node_modules`, `frontend/dist`

## Fontes de verdade

- **Índice principal**: `docs/aerus_rpg_bible.md` — lista todos os documentos e seus conteúdos
- Especificação frontend: `docs/FRONTEND_SPEC.md`
- Status de implementação: `docs/IMPLEMENTATION.md`

### Lore (dividido por tema)
- Cosmologia + história: `docs/aerus_lore_cosmologia_historia.md`
- Geografia: `docs/aerus_lore_geografia.md`
- Facções + O Dome: `docs/aerus_lore_faccoes_dome.md`
- Geopolítica + eventos + economia: `docs/aerus_lore_geopolitica_economia.md`

### Mecânicas (dividido por tema)
- Magia + isekai: `docs/aerus_mechanics_magia_isekai.md`
- Raças: `docs/aerus_mechanics_racas.md`
- Selos + reputação + rumores: `docs/aerus_mechanics_sistemas.md`
- Línguas + crafting: `docs/aerus_mechanics_linguas_crafting.md`

### Classes, NPCs, Missões
- Classes base (8 classes): `docs/aerus_classes_base.md`
- Mutações formais (níveis 25/50/75/100): `docs/aerus_classes_mutacoes.md`
- NPCs principais: `docs/aerus_npcs_principais.md`
- Fichas expandidas de NPC: `docs/aerus_npcs_fichas.md`
- Guia do GM: `docs/aerus_gm_guide.md`
- Missões por facção + arcos: `docs/campaign_missions_*.md`

### Contexto técnico (dividido)
- Visão geral + stack: `docs/PROJECT_CONTEXT_visao_stack.md`
- Arquitetura + ARD: `docs/PROJECT_CONTEXT_arquitetura_ard.md`
- ADRs + SDD: `docs/PROJECT_CONTEXT_adrs_sdd.md`
- Regras + roadmap: `docs/PROJECT_CONTEXT_regras_roadmap.md`
