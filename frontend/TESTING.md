# Aerus Game Master Platform End-to-End Manual Validation Guide

Manual guide for validating the full Aerus Game Master Platform experience through the web interface.

O objetivo aqui nao e testar componentes isolados do frontend. O objetivo e confirmar que:

1. A interface envia os dados corretos.
2. O backend aceita, persiste e processa esses dados.
3. O frontend reflete a resposta real do backend sem inconsistencias.
4. O fluxo completo continua estavel entre login, criacao, jogo, streaming, persistencia e reconexao.

## 1. Pre-requisitos

Antes de abrir o navegador, confirme:

1. Backend rodando em `http://localhost:8000`.
2. Frontend rodando em `http://localhost:5173`.
3. Backend configurado para validacao local-first (`AERUS_LOCAL_ONLY=true`).
4. Pelo menos um código de convite disponível.
5. Se quiser validar BYOK, ter uma chave OpenRouter de teste em mãos.

## 2. Subida do ambiente

### Backend

No diretório `backend/`:

```bash
.venv/Scripts/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env
```

### Frontend

No diretório `frontend/`:

```bash
npm install
npm run dev
```

## 3. Preparacao dos dados de teste

### Gerar código de convite

No backend, use um destes caminhos:

```bash
curl -X POST http://localhost:8000/admin/invite
```

ou a task já existente do projeto.

### Usuarios sugeridos

Use nomes simples para facilitar a inspecao visual:

- `kael_test`
- `lyra_test`
- `nox_test`

## 4. Escopo da validacao

Cada cenario abaixo deve ser lido como um teste E2E via interface.

Em cada etapa, valide sempre tres coisas:

1. O que a UI faz imediatamente.
2. O que isso prova sobre o backend.
3. O que volta para a UI depois do processamento.

## 5. Checklist E2E via interface

## 5.1 Login e primeiro acesso

### Cenário A — primeiro acesso com invite

1. Abrir a rota inicial `/`.
2. Confirmar que a aba ativa é `Primeiro acesso`.
3. Preencher `Invite code`, `Username` e `Password`.
4. Clicar em `Entrar no mundo`.

**Esperado na interface:**

- Sem erro visual.
- Redirecionamento para `/character`.
- Token salvo e sessão ativa.

**O que isso valida no backend:**

- O invite foi aceito e consumido corretamente.
- O usuario foi criado com sucesso.
- O token JWT retornado esta valido.
- O frontend conseguiu usar a resposta real da API sem fallback artificial.

### Cenário B — login de conta existente

1. Voltar para `/`.
2. Trocar para a aba `Já tenho conta`.
3. Preencher `Username` e `Password` já criados.
4. Clicar em `Entrar`.

**Esperado na interface:**

- Se o personagem já existir, ir para `/game`.
- Se o personagem ainda não existir, ir para `/character`.

**O que isso valida no backend:**

- A autenticacao funciona para conta ja persistida.
- O backend consegue diferenciar conta com personagem criado e conta sem personagem.
- O frontend esta interpretando corretamente o estado retornado pela API.

### Cenário C — credenciais inválidas

1. Informar senha errada.
2. Enviar o formulário.

**Esperado na interface:**

- Mensagem de erro visível.
- Sem redirecionamento.

**O que isso valida no backend:**

- O backend rejeita credenciais invalidas.
- O frontend nao mascara erro de autenticacao como sucesso.

## 5.2 Criacao de personagem

1. Na tela `/character`, preencher `Nome`.
2. Alterar a `Raça` no select.
3. Clicar em pelo menos duas facções e observar a troca visual.
4. Preencher `Backstory` com menos de 50 caracteres.

**Esperado na interface:**

- Botão de submit desabilitado.

**O que isso valida no fluxo completo:**

- O frontend esta bloqueando envio invalido antes de chamar a API.
- O formulario evita requests ruins para o backend.

5. Completar `Backstory` com pelo menos 50 caracteres.
6. Clicar em `Entrar no mundo`.

**Esperado na interface:**

- Requisição concluída sem erro.
- Redirecionamento para `/game`.
- O backend infere a classe usando modelo local com fallback determinístico.

**O que isso valida no backend:**

- O personagem foi persistido com nome, raca, faccoes e backstory.
- A inferencia de classe foi executada no backend.
- O estado inicial do personagem ficou consistente o bastante para abrir o jogo.

## 5.3 Intro isekai

Na primeira entrada do personagem no jogo:

1. Aguardar o evento de convocação.
2. Ler a narrativa da intro.
3. Confirmar que o objetivo secreto aparece na tela.
4. Clicar para entrar no jogo.

**Esperado na interface:**

- Intro aparece apenas quando ainda não foi concluída.
- Objetivo secreto é exibido ao jogador.
- Após entrar, a interface principal é liberada.

**O que isso valida no backend:**

- O backend gerou a convocacao inicial.
- O objetivo secreto foi atribuido ao personagem.
- O estado de introducao foi persistido para nao repetir indevidamente.

## 5.4 Carregamento do estado principal do jogo

Validar em `/game`:

1. `NarrativePanel` visível.
2. `CharacterSheet` visível.
3. `ActionInput` visível.
4. `EventLog` visível.
5. `ConnectionStatus` visível.
6. Botão de `VolumeSettings` visível.
7. Botão de `BYOK` visível.

**Esperado na interface:**

- Nenhum componente principal quebrado.
- Layout responsivo em largura normal de desktop.

**O que isso valida no backend:**

- O carregamento inicial do estado do jogo retornou dados suficientes para montar a tela.
- A ficha, historico, conexao e eventos vieram com estrutura compativel com a UI.

## 5.5 Envio de acao e resolucao de turno

1. Digitar uma ação simples em `ActionInput`.
2. Clicar em `Enviar`.

**Esperado na interface:**

- Input limpa após envio.
- Botão fica temporariamente bloqueado.
- Countdown `Aguardando outros jogadores...` aparece.
- Quando a resposta do GM chegar, a narrativa começa a preencher o histórico.

**O que isso valida no backend:**

- A acao saiu do frontend e chegou ao backend via WebSocket.
- O backend registrou a acao do jogador.
- O ciclo de processamento do GM foi disparado.
- O retorno do turno foi entregue de volta ao frontend sem quebrar o protocolo.

### Validacao de macro

1. Abrir `CharacterSheet`.
2. Criar uma macro simples, por exemplo `/golpe`.
3. Voltar ao input.
4. Digitar exatamente `/golpe`.
5. Enviar.

**Esperado na interface:**

- O frontend expande a macro antes do envio.

**O que isso valida no fluxo completo:**

- A expansao local continua compativel com o payload aceito pelo backend.
- O backend processa a acao expandida normalmente no turno.

## 5.6 Historico, streaming e consistencia do retorno

1. Enviar 2 ou 3 ações seguidas, aguardando as respostas.
2. Observar o `NarrativePanel` e o histórico.

**Esperado na interface:**

- Tokens narrativos aparecem progressivamente.
- Ao final do turno, o stream encerra corretamente.
- Histórico mantém entradas de jogador e GM.

**O que isso valida no backend:**

- O backend esta emitindo chunks/tokens de narrativa no formato esperado.
- O encerramento do stream ocorre sem deixar a UI presa em estado intermediario.
- O historico persistido e o historico exibido continuam coerentes entre turnos.

## 5.7 Event log

Durante os turnos:

1. Abrir o `EventLog`.
2. Confirmar que eventos de jogo entram na lista.

**Esperado na interface:**

- Os eventos mais recentes aparecem.
- O log mantém no máximo a janela configurada pelo frontend/store.

**O que isso valida no backend:**

- O backend esta emitindo eventos estruturados durante o turno.
- O frontend esta consumindo os eventos corretos, nao apenas renderizando placeholders locais.

## 5.8 CharacterSheet e persistencia de edicoes

### Backstory

1. Abrir a área da ficha relacionada ao backstory.
2. Alterar o texto.
3. Salvar.

**Esperado na interface:**

- Feedback visual coerente.
- Estado do personagem atualizado sem quebrar a tela.

**O que isso valida no backend:**

- O backend aceitou a atualizacao do backstory.
- A leitura seguinte do personagem reflete a alteracao persistida.

### Spell aliases

1. Abrir a seção de magias.
2. Selecionar um elemento existente.
3. Informar um alias.
4. Salvar.

**Esperado na interface:**

- Alias aparece imediatamente na UI.
- Persistência backend funcionando.

**O que isso valida no backend:**

- O alias foi salvo e associado ao elemento correto.
- Um reload da pagina deve manter o alias carregado da API, nao apenas do estado local.

### Macros

1. Abrir a seção de macros.
2. Criar uma macro nova.
3. Salvar.

**Esperado na interface:**

- Macro aparece imediatamente.
- Pode ser usada no `ActionInput`.

**O que isso valida no backend:**

- A macro foi persistida de forma duravel.

## 5.9 Missao cooperativa inicial obrigatoria

1. Abrir duas sessões (dois usuários diferentes) e entrar no jogo.
2. Confirmar na ficha de ambos:
   - Local compartilhado: `Ilhas de Myr`.
   - Seção `Missão Cooperativa Inicial` com status `Ativa (bloqueante)`.
   - Progresso inicial `0/N`.
3. Enviar uma ação com o jogador A e validar progresso atualizado para ambos.
4. Enviar uma ação com o jogador B e validar conclusão quando todos os vivos participarem.

**Esperado na interface:**

- O progresso sobe em tempo real via evento `COOP_MISSION`.
- Quando todos os jogadores vivos participam, o status muda para `Concluída`.

**O que isso valida no backend:**

- Flags cooperativas persistidas em `quest_flags`.
- Missão obrigatória bloqueante até completar a participação coletiva.

## 5.10 Balanceamento por quantidade de jogadores

1. Executar um turno com 1 jogador e abrir `Debug` -> `Snapshot`.
2. Registrar em `runtime` os campos `alive_players`, `encounter_scale_preview` e `boss_scale_steps_preview`.
3. Conectar mais jogadores (mesa de grupo) e repetir o snapshot.
4. Validar que:
   - `alive_players` aumentou,
   - `encounter_scale_preview` aumentou,
   - `boss_scale_steps_preview` avançou por degraus de 2 jogadores.

**Esperado na interface:**

- Confrontos com mais jogadores retornam narrativa com maior pressão/tática.
- Boss mantém base e sobe dificuldade apenas em degraus de 2 jogadores.

**O que isso valida no backend:**

- Prompt do GM recebe e aplica escala por party size.
- Curva especial de boss foi injetada no contrato de decisão do GM.

## 6. Automação E2E (Playwright Python)

No diretório `backend/`:

```bash
.venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -v -s
```

Cobertura automatizada atual:

- `test_full_e2e_flow_via_frontend`
- `test_multiplayer_cooperative_mission_flow`
- `test_scaling_preview_increases_from_solo_to_group`

## 5.9 Painel de volume

1. Clicar no botão de `VolumeSettings`.
2. Alterar os sliders de `Música`, `Efeitos` e `Ambiente`.
3. Fechar e reabrir o painel.
4. Recarregar a página.

**Esperado na interface:**

- Valores persistem.
- Música idle reage ao estado de conexão/stream.

**O que isso valida no fluxo real:**

- O frontend esta sincronizando corretamente estado de audio e estado de jogo.
- Mudancas de status recebidas do backend impactam o comportamento esperado da camada de audio.

## 5.10 Painel BYOK

1. Clicar no botão `BYOK`.
2. Confirmar abertura do painel.
3. Inserir uma chave OpenRouter de teste.
4. Clicar em `Salvar chave`.

**Esperado na interface:**

- Mensagem de sucesso visível.
- Sem crash na tela.

**O que isso valida no backend:**

- A API de registro da chave respondeu com sucesso.
- A chave foi aceita pelo backend no formato esperado.
- O frontend esta tratando resposta e erro reais da API.

### Cenário inválido

1. Abrir o painel BYOK.
2. Tentar salvar vazio.

**Esperado na interface:**

- Mensagem de erro local no próprio painel.

**O que isso valida no fluxo completo:**

- O frontend aplica validacao basica antes de enviar request desnecessaria.

## 5.11 Reconexao WebSocket

1. Abrir o jogo.
2. Desligar temporariamente o backend ou derrubar a conexão de rede.
3. Observar `ConnectionStatus`.
4. Restaurar backend/conexão.

**Esperado na interface:**

- Estado muda para `reconnecting`.
- Após retorno, reconecta sem recarregar a página.
- Histórico e estado atual continuam coerentes.

**O que isso valida no backend e no protocolo:**

- O backend volta a aceitar a sessao reconectada.
- O frontend recompõe a conexao sem perder o estado essencial.
- O contrato WebSocket continua consistente apos falha transiente.

## 5.11.1 Validacao via Debug Snapshot (backend vs frontend)

Com o jogo aberto em `/game`:

1. Abrir o painel `Debug` no canto inferior direito.
2. Clicar em `Snapshot`.
3. Conferir bloco `Comparação backend vs frontend`.

**Esperado na interface:**

- Snapshot carrega sem erro de autenticação.
- Mostra dados de backend e frontend lado a lado.
- Exibe `Estado local consistente com snapshot do backend` quando não há divergência.

**O que isso valida no backend e no frontend:**

- API `GET /debug/state` responde com dados reais do estado persistido.
- Hidratação de estado do frontend está coerente com o estado do servidor.
- Diferenças de `turn`, `class`, `hp/mp/stamina` e `campaign_paused` são detectáveis sem inspeção manual de banco.

### Cenário com divergência forçada

1. Enviar uma ação e clicar `Snapshot` imediatamente durante processamento do turno.
2. Repetir o snapshot após `stream_end`.

**Esperado na interface:**

- Pode haver divergência transitória durante processamento.
- Após término do turno, os diffs devem desaparecer ou reduzir para casos esperados.

## 5.12 Eventos especiais de gameplay

Alguns eventos exigem ajuda do backend ou turnos especificos. Validar quando ocorrerem no fluxo normal do jogo.

### DiceRoll

**Esperado na interface:**

- Overlay/animação de dado aparece.
- Critical/fumble são indicados corretamente.

**O que isso valida no backend:**

- O backend esta emitindo evento de rolagem com payload coerente.
- O frontend interpreta corretamente sucesso, falha critica e falha comum.

### Class mutation

**Esperado na interface:**

- Ao atingir o marco de nível configurado, a classe exibida na ficha muda.
- O evento aparece no fluxo do jogo.

**O que isso valida no backend:**

- A progressao foi aplicada no estado persistido.
- A mutacao de classe nao foi apenas cosmetica; ela veio do estado real do personagem.

### Secret objective hints

**Esperado na interface:**

- O frontend recebe evento `FACTION_CONFLICT`.
- O hint aparece no fluxo/event log sem expor o objetivo completo diretamente.

**O que isso valida no backend:**

- O backend esta acompanhando progresso do objetivo secreto.
- O disparo de hint esta sendo calculado e emitido corretamente.

### Spectator mode

Quando o personagem morrer:

**Esperado na interface:**

- `SpectatorOverlay` aparece.
- A UI reflete `status: dead`.

**O que isso valida no backend:**

- O estado de morte foi persistido.
- O frontend esta reagindo ao estado real do personagem, nao a uma simulacao local.

## 5.13 Responsividade minima

Validar em largura reduzida ou DevTools responsivo:

1. Abrir `/game`.
2. Simular largura mobile/tablet.

**Esperado na interface:**

- `layout-grid` vira uma coluna.
- `CombatOrder` some em telas menores.
- `EventLog` e `ConnectionStatus` deixam de conflitar visualmente.
- Botões de volume e BYOK continuam acessíveis.

**O que isso valida no fluxo da aplicacao:**

- A interface continua utilizavel durante o jogo real em telas menores.
- O consumo das respostas do backend continua funcional mesmo com layout reduzido.

## 6. Roteiro rapido de smoke test E2E

Se quiser uma validacao curta da aplicacao inteira pela interface:

1. Login/redeem.
2. Criar personagem.
3. Confirmar intro isekai.
4. Entrar no jogo.
5. Enviar uma ação.
6. Validar narrativa e event log.
7. Criar uma macro e usar no input.
8. Salvar um alias de magia.
9. Abrir `VolumeSettings` e mudar volumes.
10. Abrir `BYOK` e salvar uma chave.
11. Recarregar a página e confirmar que a sessão continua funcional.

## 7. Confirmacoes obrigatorias apos reload

Depois de executar os cenarios principais, recarregue a pagina em `/game` e confirme:

1. A sessao continua valida sem pedir novo login indevidamente.
2. O personagem carregado e o mesmo criado anteriormente.
3. Backstory editado continua salvo.
4. Macros continuam salvas.
5. Spell aliases continuam salvos.
6. O objetivo secreto continua consistente com o personagem.
7. O historico e o estado geral nao voltaram para um estado inicial incorreto.

Se algum desses itens falhar, o problema nao e apenas visual. Isso indica falha de persistencia, sincronizacao ou reidratacao entre backend e frontend.

## 8. Comandos de apoio

### Testes automatizados

```bash
npm run test
```

### E2E via Playwright (Python)

No diretório `backend/`:

```bash
.venv/Scripts/pip install -r requirements-e2e.txt
.venv/Scripts/python -m playwright install chromium
.venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -v
```

### Build de validação

```bash
npm run build
```

## 9. Criterio de aceite da aplicacao via frontend

A aplicacao e considerada validada manualmente por este roteiro quando:

1. O fluxo `/` -> `/character` -> `/game` funciona sem erro e sem inconsistencias de estado.
2. Acoes enviadas pela interface chegam ao backend, sao processadas e retornam como narrativa e eventos coerentes.
3. Edicoes de ficha feitas pela UI persistem de verdade apos reload.
4. Intro, objetivo secreto, hints, rolagens, mutacao de classe e modo espectador aparecem quando o backend os dispara.
5. WebSocket reconecta corretamente sem corromper sessao nem historico.
6. BYOK e configuracoes de audio funcionam sem quebrar o fluxo principal.
7. O comportamento observado na interface confirma que frontend e backend respondem como uma unica aplicacao integrada.
8. Testes automatizados e build continuam passando como apoio, mas nao substituem esta validacao E2E.
