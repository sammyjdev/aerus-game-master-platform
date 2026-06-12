# Resumo Tecnico do Projeto Aerus RPG

## 1. Visao geral

Aerus e uma plataforma de RPG narrativo cooperativo multiplayer orientada por IA.
O repositorio segue padrao monorepo com backend FastAPI e frontend React.

Objetivo tecnico principal:

- processar acoes de varios jogadores em tempo real
- manter estado persistente da campanha
- montar contexto de LLM com lore + historico + estado
- transmitir narrativa token a token por WebSocket

## 2. Estrutura do repositorio

- backend/: API, WebSocket, regras de jogo, persistencia e testes
- frontend/: SPA React + TypeScript para experiencia do jogador
- docs/: especificacoes, lore tecnico-funcional e contexto arquitetural
- lore/: fonte canonica de mundo e bestiario
- scripts/: utilitarios de sincronizacao e validacao

## 3. Stack e dependencias

### 3.1 Backend

Runtime e framework:

- Python 3.11+
- FastAPI 0.135.1
- Uvicorn 0.42.0

Persistencia e dados:

- SQLite via aiosqlite 0.22.1
- ChromaDB 1.5.5 para busca vetorial de lore

Modelagem e seguranca:

- Pydantic 2.12.5
- pydantic-settings 2.13.1
- cryptography 46.0.5
- python-jose 3.5.0
- passlib + bcrypt

Rede e utilitarios:

- httpx
- python-dotenv
- pyyaml

Testes:

- pytest
- pytest-asyncio

### 3.2 Frontend

Core:

- React 19
- TypeScript 5.9
- Vite 8

Estado, roteamento e validacao:

- Zustand
- React Router DOM 7
- Zod

Conteudo, audio e UI:

- react-markdown
- rehype-sanitize
- howler
- framer-motion
- i18next + react-i18next

Qualidade e testes:

- ESLint 9
- Vitest 4
- Testing Library
- jsdom

## 4. Arquitetura backend

### 4.1 Camadas

Padrao alvo:

- Transporte/API: backend/src/main.py
- Aplicacao: backend/src/application/
- Infraestrutura: backend/src/infrastructure/
- Core legado em migracao: modulos em backend/src/\*.py

Regras de arquitetura explicitadas no projeto:

- zero regra de negocio em main.py
- SQL centralizado em state_manager.py
- ChromaDB centralizado em vector_store.py

### 4.2 Modulos principais

- game_master.py: orquestracao de turnos, chamada de modelos, parse de eventos
- state_manager.py: acesso SQLite, transacoes, leitura/escrita de estado
- context_builder.py: montagem em camadas do contexto para LLM
- vector_store.py: ingestao e retrieval semantico de lore/bestiario
- connection_manager.py: gerenciamento de salas WS e broadcast
- ws_contracts.py: contrato tipado de mensagens de saida por WebSocket
- billing_router.py: roteamento de modelo/chave (BYOK/admin)
- travel_manager.py: rotas, progresso de viagem e encontros
- behavior_trajectory.py: trilha comportamental para mutacoes de classe
- memory_manager.py: pontuacao/selecionamento de memorias episodicas
- rumor_manager.py: rumores por faccao e gating por tensao
- reputation_gates.py: desbloqueios por reputacao com guard de one-shot
- time_manager.py: calendario persistente do mundo
- inventory_manager.py: peso, capacidade e economia de moedas
- recipe_manager.py: carga de receitas de crafting
- migration_runner.py: execucao sequencial de migrations

### 4.3 Lifecycle da aplicacao

No startup (lifespan do FastAPI):

- inicializa banco
- carrega receitas
- ingere bestiario e lore no ChromaDB

HTTP middleware:

- gera X-Request-ID
- loga inicio/fim com duracao
- adiciona request id na resposta

CORS:

- fail-closed por ALLOWED_ORIGINS (default localhost:5173)

## 5. Persistencia e modelo de dados

Banco principal:

- SQLite local (arquivo aerus.db)

Migracoes observadas:

- 13 migrations SQL em backend/migrations (001 a 013)
- cobertura de schema inicial, economia, idiomas/backstory, episodios, skills e magic level

Estado do jogador (alto nivel):

- identidade, nivel e experiencia
- atributos base (str/dex/int/vit/luck/cha)
- HP/MP/Stamina
- inventario, peso, capacidade e moedas
- condicoes e efeitos
- proficiencias de arma/magia
- macros e aliases de magia
- milestones passivas

Regras de progressao tecnicas destacadas:

- capanhas de atributos com teto por atributo e teto total
- cap de magia global
- progressao de rank elemental vinculada a magic level
- custo de PP escalonado por rank/level

## 6. Contrato de comunicacao em tempo real (WebSocket)

Fonte de verdade backend:

- backend/src/ws_contracts.py

Espelho frontend:

- frontend/src/types/wsContracts.ts (Zod)

Tipos de mensagem cobertos:

- narrativa: narrative_token, stream_end, gm_thinking
- estado: game_event, state_update, full_state_sync, history_sync
- dados de rolagem: dice_roll, request_dice_roll, dice_roll_resolved, dice_result
- midia: audio_cue, boss_music, image_ready
- autenticacao: token_refresh
- isekai/objetivos: isekai_convocation, faction_objective_update
- sistema: milestone, seal_event, error

Garantia de robustez do cliente:

- parse por discriminated union do Zod
- estrategia safeParse para ignorar payload invalido em caminhos nao criticos

## 7. Arquitetura frontend

Organizacao principal:

- pages/: composicao de telas
- features/: barrel por dominio
- components/: blocos de UI por area (character, combat, travel, narrative etc.)
- hooks/: integracoes (inclui websocket)
- store/gameStore.ts: estado global com Zustand
- api/: wrappers HTTP
- i18n/: internacionalizacao

Estado global relevante (gameStore):

- token e status de conexao
- estado de jogo (jogador atual, outros jogadores, mundo, historico)
- fila/buffer de narrativa
- rolagens pendentes e resolucoes
- log de eventos e debug
- reputacao por faccao
- estado de iniciativa/turnos

Front e backend operam no modelo:

- backend emite evento tipado
- frontend valida schema
- frontend aplica delta/full sync no store

## 8. Configuracao de campanha e IA

Arquivo central:

- backend/config/campaign.yaml

Pontos tecnicos importantes:

- max_players: 5
- linguagem da campanha: pt
- dificuldade: brutal, permadeath true
- janela de batch de acoes: 3 segundos
- timeout de pensamento do GM: 15 segundos
- historico no contexto: 10 turnos
- level cap: 100

Selecao de modelo por tensao:

- default/fallback e thresholds low/medium/high/critical
- suporte a modelos remotos (OpenRouter) e fallback local

Orcamento de contexto por camadas:

- L0 estatico
- L1 campanha
- L2 estado
- L3 historico
- memoria episodica
- retrieval de lore
- hard cap total

## 9. Lore, conhecimento e retrieval

Separacao de responsabilidades:

- lore/ = fonte canonica autoral
- backend/config/ = copia operacional usada em runtime

Vetorizacao:

- ingestao de world + bestiary no startup
- busca semantica para grounding narrativo

Observacao operacional:

- alteracoes em lore exigem sincronizacao com backend/config para refletir em runtime

## 10. Seguranca e autenticacao

Modelo atual:

- convite para cadastro inicial
- login com username/password
- JWT para autenticacao
- sessao persistida no backend

Mecanismos adicionais:

- hash de senha
- endpoint admin protegido por X-Admin-Secret
- API keys BYOK cifradas

## 11. Build, execucao e comandos uteis

Backend (dev):

- uvicorn src.main:app --reload --env-file .env

Frontend (dev):

- npm run dev

Testes backend:

- pytest tests/ -v

Testes frontend:

- npm run test

Build frontend:

- npm run build

Atalhos de automacao disponiveis:

- tarefas VS Code para setup, install, run, test, clean e geracao de chaves
- Makefile com comandos de setup, dev e sincronizacao de lore

## 12. Qualidade e testes

Backend:

- suite com testes de auth, state_manager, context_builder, game_master, vector_store, cors, ws contracts, inventario e mais
- existe camada E2E em backend/e2e
- existe framework de avaliacao comportamental do GM em backend/eval

Frontend:

- unit tests com Vitest + Testing Library
- guia de validacao manual em frontend/TESTING.md

## 13. Limitacoes e restricoes operacionais

Restricao de deploy observada:

- fly.toml define max_machines = 1
- escalabilidade horizontal exige migracao para PostgreSQL antes de sharding real

Artefatos locais nao versionados:

- backend/.venv
- backend/aerus.db
- backend/chroma_db
- frontend/node_modules
- frontend/dist

## 14. Fontes de verdade internas do projeto

Documentos de referencia:

- docs/aerus_rpg_bible.md (indice principal)
- docs/FRONTEND_SPEC.md
- docs/IMPLEMENTATION.md
- docs/PROJECT*CONTEXT*\*.md

Contratos criticos:

- backend/src/ws_contracts.py
- frontend/src/types/wsContracts.ts

## 15. Conclusao tecnica

O projeto apresenta arquitetura moderna, modular e orientada a eventos para RPG narrativo com IA.
Os pilares tecnicos sao:

- backend assincrono com regras centralizadas por modulo
- persistencia relacional local com migrations evolutivas
- retrieval semantico para grounding narrativo
- frontend reativo com estado global robusto
- contrato WS tipado e validado ponta a ponta

Em termos de maturidade de engenharia, ha sinais fortes de:

- separacao de responsabilidades
- cobertura de testes relevante
- documentacao extensa
- caminho de evolucao arquitetural ja definido
