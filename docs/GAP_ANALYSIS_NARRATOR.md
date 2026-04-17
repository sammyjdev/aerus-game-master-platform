# GAP ANALYSIS NARRATOR — AERUM RPG

> Documento de análise de gaps para treinamento do modelo narrador (SLM fine-tune).
> Produzido em: 2026-04-14
> Baseado em leitura integral de toda a documentação listada.

---

## LEGENDA

- ✅ Coberto — regra, exemplo ou protocolo documentado na fonte indicada.
- PARTIAL — existe algo, mas está incompleto ou ambíguo para o GM.
- ❌ MISSING — não existe documentação relevante.
- **CRÍTICO** — ausência quebra a sessão.
- **ALTO** — ausência causa improv errado.
- **MÉDIO** — ausência torna a narração genérica.

---

## SEÇÃO 1 — MECÂNICAS QUE DITAM A NARRATIVA

---

### COMBATE

---

#### Iniciativa e ordem de turno

- (a) Arbitration rule: ❌ MISSING — Nenhum documento define atributo usado, dado rolado, ni desempates.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem regra para empate, inimigos múltiplos, ou "surprise round".

---

#### Ataque bem-sucedido por tipo (físico, mágico, à distância)

- (a) Arbitration rule: ❌ MISSING — aerus_base_classes.md descreve papéis de combate mas não define dado de ataque, DC de defesa, nem fórmula de dano.
- (b) Narrative example: PARTIAL — narration_bible.md e narration_bible_kernel.md têm diretrizes de tom ("frases secas, tensas") mas sem exemplo de resolução de acerto.
- (c) Edge cases: ❌ MISSING — sem regra para ataque vs. armadura de Keth, ataque com selo mágico em zona corrupta, ou alcance máximo.

---

#### Ataque falho e exposição de flanco

- (a) Arbitration rule: ❌ MISSING — nenhuma mecânica de "miss" documentada; não há consequência mecânica por falha.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Crítico (natural 20) — o que muda na narrativa

- (a) Arbitration rule: ❌ MISSING — nenhuma definição de "natural 20" para o Aerum; a tabela de atributos existe (STR, DEX, INT, VIT, LUK, CAR) mas sem mecânica de crit.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Falha crítica (natural 1) — consequência obrigatória

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Dano por tipo de elemento (fogo, gelo, terra, ar, energia, espírito)

- (a) Arbitration rule: PARTIAL — world_kernel.md lista efeitos de corrupção por elemento ("fire -> burns the caster; water -> necrotizes; earth -> erodes consciousness; air -> attracts an Echo; energy -> causes a Surge; spirit -> awakens something"), MAS apenas como risco de backfire, não como fórmula de dano contra alvos.
- (b) Narrative example: ❌ MISSING — sem exemplo de como narrar acerto de gelo vs criatura de fogo, por exemplo.
- (c) Edge cases: ❌ MISSING — sem regra para imunidade, resistência, ou cura por elemento afim.

---

#### Dano em zona de corrupção (magia instável)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_magic_isekai.md §Aeridian Fragments diz que dentro de 50m de um Fragmento a magia é completamente estável; aerus_mechanics_languages_crafting.md §Keth by Grade lista grades de estabilização; world_kernel.md lista efeitos de backfire. Mas não há tabela de probabilidade de instabilidade por zona, nem penalidade numérica.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para magia defensiva em zona corrupta, nem diferença entre zona T2 vs T4.

---

#### Morte imediata vs 0 HP vs estabilização

- (a) Arbitration rule: ❌ MISSING — campaign.yaml confirma `permadeath: true` e `difficulty: brutal` mas não define limiar de HP, "death saves", nem protocolo de estabilização.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Character Death tem fragmento de voz ("There is no heroic final monologue, only the abrupt violence of a life interrupted") mas sem protocolo mecânico.
- (c) Edge cases: ❌ MISSING — sem regra para personagem a 1 HP, personagem inconsciente, estabilização por aliado.

---

#### Morte permanente (permadeath) — protocolo narrativo

- (a) Arbitration rule: PARTIAL — campaign.yaml `permadeath: true` confirma que morte é permanente; aerus_mechanics_magic_isekai.md §Model: Log Horizon confirma "Death is real death." Mas não há protocolo de o que o GM deve fazer imediatamente após a morte.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Character Death tem 4 linhas de voz mas não diz se o GM pausa, faz transição, ou continua a cena.
- (c) Edge cases: ❌ MISSING — sem regra para morte por dano de área (quem morre primeiro?), morte durante combate com múltiplos jogadores.

---

#### Personagem morto vira espectador — transição narrativa

- (a) Arbitration rule: ❌ MISSING — nenhum documento descreve o que acontece mecanicamente após a morte: pode o jogador ver a cena? participar? criar novo personagem imediatamente?
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para "espectador com objetivo secreto ainda ativo" ou "espectador que conhece informação vital".

---

#### Múltiplos atacantes no mesmo alvo

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Ataque de área em grupo misto (aliados + inimigos)

- (a) Arbitration rule: ❌ MISSING — campaign.yaml tem `friendly_fire: false` mas não explica como isso interage com magia de área narrativamente.
- (b) Narrative example: ❌ MISSING — sem exemplo de como narrar um feitiço de área que tecnicamente não afeta aliados mas os coloca em risco visível.
- (c) Edge cases: ❌ MISSING — e se o alvo aliado estiver incapacitado dentro da zona?

---

#### Combate em terreno especial (ruína, zona corrompida, água, altitude)

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Combat Scenes menciona "terrain" como elemento que torna a luta única, mas sem modificadores mecânicos.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Danger Zone tem fragmento de voz para Ash Desert, mas não para combate dentro de zona corrompida.
- (c) Edge cases: ❌ MISSING — sem regra para combate dentro de Ondrek Pass (zona sem magia), água, ou altitude extrema.

---

#### Fuga de combate — quando é possível, como narrar

- (a) Arbitration rule: ❌ MISSING — nenhum documento define condição de fuga (HP limiar? ação específica? custo?).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem regra para fuga quando cercado, fuga de boss, ou perseguição após fuga.

---

#### Rendição de inimigo — o que acontece mecanicamente

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para inimigo que se rende e depois trai, ou para executar inimigo rendido e consequência de reputação.

---

#### Monstro com fase (boss phase change) — gatilho e narrativa

- (a) Arbitration rule: ❌ MISSING — nenhum limiar de HP ou condição definida para phase change.
- (b) Narrative example: ✅ aerus_gm_guide.md §Boss Phase Change — fragmento exemplar completo ("The second phase does not announce itself... The party has one turn.").
- (c) Edge cases: ❌ MISSING — sem regra para quantas fases existem, se a fase change cura HP, ou se o GM deve avisar com antecedência.

---

#### Combate contra NPC aliado (traição, controle mental)

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para "NPC aliado sob controle mental ataca jogador" ou "jogador com objetivo secreto de eliminar o aliado".

---

#### Batalha enquanto outro jogador executa ação diferente

- (a) Arbitration rule: PARTIAL — CLAUDE.md menciona sistema de batch de 3s (`action_batch_window_seconds: 3`) mas não define como o GM resolve simultaneidade narrativa.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para jogador B negociando enquanto jogador A está em combate na mesma cena.

---

### CONDIÇÕES E ESTADOS

---

#### Lista completa de condições do sistema (atordoado, envenenado etc.)

- (a) Arbitration rule: ❌ MISSING — nenhum documento lista condições de status do Aerum. aerus_mechanics_systems.md não define lista de condições. Apenas world_kernel.md cita "corrupção progressiva" como efeito de backfire.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Quanto tempo dura cada condição

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Como narrar aplicação de cada condição

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Como narrar remoção de cada condição

- (a) Arbitration rule: ❌ MISSING — narration_bible_kernel.md menciona "Cura e recuperação devem indicar a fonte" mas não por tipo de condição.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Condições que interagem entre si

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Corrupção mágica progressiva — estágios e narrativa por estágio

- (a) Arbitration rule: PARTIAL — world_kernel.md lista efeitos de backfire por elemento mas sem estágios numerados ou limiar de acumulação. aerus_mechanics_magic_isekai.md menciona vulnerabilidade de Viajantes à corrupção mas sem escala.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para "personagem em estágio 3 de corrupção que usa magia de cura".

---

#### Rooting dos Viajantes — como muda a narrativa por estágio

- (a) Arbitration rule: ✅ aerus_mechanics_magic_isekai.md §Rooting — tabela de 5 períodos com sinais físicos/narrativos definidos.
- (b) Narrative example: PARTIAL — tabela descreve o sinal ("The Thread becomes perceptible as atmospheric pressure") mas não exemplifica como o GM deve narrar isso em cena.
- (c) Edge cases: ❌ MISSING — sem protocolo para jogador que tenta sair antes do rooting completo, ou para dois Viajantes em estágios diferentes na mesma cena.

---

#### Frenesi ou perda de controle do personagem

- (a) Arbitration rule: ❌ MISSING — nenhum documento define gatilho ou mecânica de frenesi/perda de controle.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### MAGIA E FIO PRIMORDIAL

---

#### Surge — o que desencadeia, como escalar, como narrar

- (a) Arbitration rule: PARTIAL — world_kernel.md define que "energy -> causes a Surge" como backfire. aerus_lore_cosmology_history.md explica que Surges são Vor'Athek pressionando contra a prisão. Mas não há tabela de DC de Surge, escala de raio, ou gatilho por nível de magia.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Danger Zone tem voz de zona de perigo mas sem exemplo específico de Surge em progresso.
- (c) Edge cases: ❌ MISSING — sem regra para Surge causado por Fragmento destruído (citado em aerus_mechanics_magic_isekai.md como "energy equivalent to a maximum-grade Surge" mas sem protocolo narrativo).

---

#### Backfire em zona corrompida — probabilidade e consequências

- (a) Arbitration rule: PARTIAL — world_kernel.md lista tipos de backfire por elemento. aerus_mechanics_languages_crafting.md §Keth by Grade implica que Keth reduz risco mas sem número. Não há tabela de probabilidade por zona (T1-T5).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem regra para personagem com Fragmento Aeridiano em zona corrupta, ou efeito de Keth Grade 4 vs Grade 1.

---

#### Dois feitiços simultâneos no mesmo alvo

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Fusão elemental (quando dois elementos interagem)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_magic_isekai.md §Alchemical Fusions tem tabela de requisitos (nível mínimo nos elementos base), mas não define o que acontece quando dois jogadores usam elementos diferentes no mesmo turno sem coordenação.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem regra para fusão não intencional (fogo vs água de dois jogadores).

---

#### Magia de cura que causa necrose (corrupção do Fio)

- (a) Arbitration rule: PARTIAL — aerus_lore_cosmology_history.md e world.md mencionam que "healing magic could cause necrosis" como efeito da corrupção do Fio; world_kernel.md lista "water -> necrotizes". Mas sem DC de quando isso acontece, nem protocolo de quanto necrose causa.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para curandeiro com Keth vs sem Keth, ou cura em zona estabilizada por Fragmento.

---

#### Spell failure parcial vs total

- (a) Arbitration rule: ❌ MISSING — nenhum documento diferencia falha parcial (efeito reduzido) de falha total (nada acontece) de backfire (efeito negativo).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Canal aberto (Canalizador) — risco e recompensa narrativa

- (a) Arbitration rule: PARTIAL — aerus_base_classes.md §Channeler descreve "Open Channel" como habilidade base que "temporarily aligns the self with a source of power for increased effect and increased risk." Mas sem definição do risco (DC? dano? duração?).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para Canalizador que mantém canal aberto por múltiplos turnos, ou canal aberto em zona corrupta.

---

#### Uso de magia sem Selo de Chama em território imperial

- (a) Arbitration rule: ✅ aerus_mechanics_magic_isekai.md §Flame Seals + aerus_mechanics_systems.md §Flame Seal System — define categorias de Selos, que usar magia sem autorização "increases institutional pressure", e que falsificações colapsam sob inspeção especializada.
- (b) Narrative example: PARTIAL — aerus_mechanics_systems.md §Black Market Role e §Gameplay Effects descrevem consequências abstratas mas sem exemplo concreto de cena.
- (c) Edge cases: PARTIAL — aerus_mechanics_magic_isekai.md menciona que "Kethara never adopted the system, and Myr accepts Seals but does not require them" — útil, mas sem protocolo para zona de transição (entrando em território imperial pelo mar).

---

#### Fragmento Aeridiano próximo — como muda a magia

- (a) Arbitration rule: ✅ aerus_mechanics_magic_isekai.md §Aeridian Fragments — "Within a 50-meter radius, magic becomes completely stable."
- (b) Narrative example: PARTIAL — aerus_lore_dome_factions.md §The Dome Mark menciona que a Marca "pulses more intensely near Aeridian Fragments" mas sem exemplo narrativo de o que o GM descreve para o jogador.
- (c) Edge cases: ❌ MISSING — sem protocolo para dois Fragmentos próximos, Fragmento corrompido (caso Valdek IV), ou Fragmento destruído.

---

#### Cristal do Silêncio — efeito na magia ao redor

- (a) Arbitration rule: PARTIAL — aerus_lore_cosmology_history.md menciona que "emits a low-frequency sound that humans do not hear but animals avoid" e que "the vault should never remain open for long." campaign_mission_arcs.md §Arc III menciona que o Guild quer que os Viajantes carreguem o Cristal para o Last Chamber. Mas sem definição de raio de efeito, efeito em spells, ou interação com zonas corruptas.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### PROGRESSÃO E MUTAÇÃO

---

#### Level up durante sessão — quando acontece, como narrar

- (a) Arbitration rule: PARTIAL — narration_bible_kernel.md menciona "Ações com impacto real... devem render XP explícito no estado." campaign.yaml define `level_cap: 100` e `passive_milestone_every_points: 25`. Mas não há DC de XP necessário por nível, nem protocolo de quando interromper a cena para narrar o level up.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para dois jogadores evoluindo no mesmo turno, ou evolução durante combate.

---

#### Milestone passivo desbloqueado — interrupção narrativa ou não

- (a) Arbitration rule: ❌ MISSING — campaign.yaml define `passive_milestone_every_points: 25` e `class_mutation_every_levels: 25` mas sem protocolo narrativo de como o GM comunica o desbloqueio.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Mutação formal (níveis 25/50/75/100) — protocolo de narrativa

- (a) Arbitration rule: PARTIAL — aerus_class_mutations.md §Mutation Framework define outcomes esperados por nível mas sem protocolo de como o GM apresenta as opções ao jogador ou como narra a transformação.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para mutação rejeitada pelo jogador, ou mutação em contexto de combat ativo.

---

#### Atributo atingindo o cap (250 por atributo) — consequência narrativa

- (a) Arbitration rule: PARTIAL — campaign.yaml define `attribute_per_cap: 250` e `attribute_campaign_cap: 500`. Mas sem protocolo narrativo de o que acontece quando um atributo é maxado.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### XP por tipo de ação (combate, diplomacia, objetivo)

- (a) Arbitration rule: PARTIAL — narration_bible_kernel.md: "Ações com impacto real, que resolvem obstáculo, salvam alguém ou fazem a história avançar, devem render XP explícito no estado." Mas sem tabela de quantidade de XP por tipo de ação.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para diplomacia que falha parcialmente, ou objetivo completado de forma não prevista.

---

#### Classe inferida errada — como corrigir sem quebrar a narrativa

- (a) Arbitration rule: ❌ MISSING — CLAUDE.md menciona `behavior_trajectory.py` que "scores player episodes by action category; drives class mutation path selection" mas sem protocolo de correção narrativa.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Dois jogadores evoluindo ao mesmo tempo

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### CRAFTING E ECONOMIA

---

#### Tentativa de craft bem-sucedida — narrativa do processo

- (a) Arbitration rule: ✅ aerus_mechanics_languages_crafting.md §Principle — "Crafting is resolved narratively by the GM using the recipe tables... The GM describes the process, calls for an attribute check against a difficulty class, and narrates the result."
- (b) Narrative example: ❌ MISSING — o documento define o protocolo mas não fornece exemplo de narração de craft bem-sucedido.
- (c) Edge cases: ❌ MISSING — sem protocolo para craft parcialmente bem-sucedido (passou DC mas por 1), ou craft em condições adversas.

---

#### Falha no craft — consequência (item quebrado, ingrediente perdido, acidente)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_languages_crafting.md define o check (INT DC X ou STR DC X) mas não define o que acontece em falha: o ingrediente é consumido? o item quebra? há dano ao artesão?
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Falha crítica no craft — consequência grave

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Craft em zona corrompida com Keth

- (a) Arbitration rule: PARTIAL — aerus_mechanics_languages_crafting.md §Keth by Grade define que Keth estabiliza magia de nível correspondente, mas sem protocolo específico para crafting em zona T3+ corrompida mesmo com Keth Grade 3.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Item consumível usado em combate — timing narrativo

- (a) Arbitration rule: ❌ MISSING — nenhum documento define se usar uma poção consome ação de turno, ação livre, ou tem restrição de timing em combate.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Troca e negociação de preço com NPC

- (a) Arbitration rule: PARTIAL — aerus_lore_geopolitics_economy.md §Regional Price Table tem preços regionais, reputation_gates.yaml tem desconto de 15% para Myr Council friendly. Mas sem protocolo de checagem de atributo para barganha.
- (b) Narrative example: PARTIAL — narration_bible.md §Resposta a ação social tem exemplo de NPC reagindo, mas sem contexto de negociação de preço especificamente.
- (c) Edge cases: ❌ MISSING — sem protocolo para negociar com NPC hostil (-50 ou abaixo), ou para item ilegal.

---

#### Compra de item ilegal (mercado cinza)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_systems.md §Black Market Role e aerus_lore_geopolitics_economy.md §Gray Market in Port Myr descrevem o mercado. aerus_main_npcs.md cita Seyla Vorn como fornecedora de Keth sem papelada. Mas sem DC de encontrar vendedor, risco de flagrante, ou consequência de reputação específica.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para item comprado no mercado negro sendo encontrado por inspeção imperial.

---

#### Item roubado sendo reconhecido por dono

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### VIAGEM E ENCONTROS

---

#### Encontro de viagem em cada tipo de terreno

- (a) Arbitration rule: ✅ aerus_travel.md §Encounter Types by Terrain + backend/config/travel.yaml §encounter_tables — tabelas completas por terreno com roll ranges, tipos e tiers.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Danger Zone tem fragmento para Ash Desert; aerus_travel.md menciona descrições curtas por tipo. Mas sem exemplos narrativos para cada encontro específico.
- (c) Edge cases: PARTIAL — aerus_travel.md §Special Location Notes cobre Gorath Fissures, Vel'Arath, Limen, Keth-Ara, Wandering Cities e Heart of Ashes com notas especiais. Mas sem protocolo para "encontro durante acampamento" ou "dois encontros no mesmo dia".

---

#### Encounter de Tier acima da party — fuga obrigatória?

- (a) Arbitration rule: PARTIAL — travel.yaml §corrupted lista "Abyss Lord — Abyss Lord encounter where escape is wiser than combat" (tier 4) mas sem mecânica de fuga obrigatória ou regra de "fight or flee" por diferença de tier.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Chegada a local novo durante missão ativa

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Arrival Scenes tem checklist de 4 pontos mas sem integração com estado de missão ativa.
- (b) Narrative example: PARTIAL — narration_bible.md §Abertura de Cena tem estrutura em 3 beats com exemplo concreto de Port Myr.
- (c) Edge cases: ❌ MISSING — sem protocolo para chegada a local onde a party é "wanted" (reputation gate `empire_hostile_wanted`).

---

#### Clima extremo durante viagem (tempestade mágica, neve ártica)

- (a) Arbitration rule: PARTIAL — travel.yaml lista "ice_storm: Blizzard with near-zero visibility and hypothermia risk" e "storm: Storm damages the ship and may push it off course" como encounter types mas sem regras mecânicas de dano ou penalidade.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para tempestade mágica vs normal, ou hipotermia em mecânica de VIT.

---

#### Viagem de barco vs terrestre — diferenças narrativas

- (a) Arbitration rule: PARTIAL — travel.yaml define speed multipliers (sea: 0.6 = mais rápido; mountain: 3.0 = mais lento) e encounter tables diferentes. Mas sem diferença narrativa explícita (desconforto, risco diferente, NPCs encontrados).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para naufrágio, abordagem pirata, ou separação de grupo em mar aberto.

---

#### Viagem pelo Cinturão Pálido (Void Zone) — efeitos especiais

- (a) Arbitration rule: PARTIAL — aerus_lore_geography.md menciona "Permanent fog, pervasive danger, and only one truly safe crossing through Ondrek Pass." aerus_mechanics_magic_isekai.md §Flame Seals implica que magia não funciona em Ondrek Pass. Mas sem tabela de efeitos de Void Zone em magia, HP, ou orientação.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para Khorathi (Body Without Thread) vs Canalizador viajando pela Void Zone.

---

#### Vel'Arath — regras especiais de entrada

- (a) Arbitration rule: PARTIAL — aerus_travel.md §Special Location Notes: "The forest decides who may enter. There is no fixed route; duration is narrative." travel.yaml nota "The forest only admits those it chooses." Mas sem critério de quem o bosque admite, nem mecânica de tentativa e recusa.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para Wandering Fae tentando entrar, ou grupo com um membro não admitido.

---

#### Coração das Cinzas — preparação narrativa obrigatória

- (a) Arbitration rule: PARTIAL — aerus_travel.md e travel.yaml listam "Extremely dangerous. Not recommended below level 100." campaign_mission_arcs.md descreve o que lá existe (Last Chamber). Mas sem checklist de preparação obrigatória (equipamento, level mínimo, proteção contra corrupção).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para party subleveled que insiste em ir.

---

#### Acampamento e descanso — quanto recupera, quanto tempo passa

- (a) Arbitration rule: PARTIAL — narration_bible_kernel.md: "O local importa: uma cama segura, templo ou estalagem melhora a recuperação; perigo e interrupção a reduzem. Cura e recuperação devem indicar a fonte: repouso leve, sono seguro, primeiros socorros, poção, ritual ou magia." Mas sem número concreto de HP/MP recuperados por tipo de descanso.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para descanso em zona corrompida (recupera menos? acumula corrupção?).

---

#### Emboscada durante descanso

- (a) Arbitration rule: ❌ MISSING — nenhum documento define penalidade de "sleeping party" (sem armadura, sem iniciativa normal, etc.).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### SOCIAL E FACÇÕES

---

#### Checagem de reputação antes de interação com NPC

- (a) Arbitration rule: ✅ aerus_mechanics_systems.md §Reputation Bands + §General Effects — define faixas e efeitos gerais. reputation_gates.yaml define gates de conteúdo desbloqueável por limiar.
- (b) Narrative example: PARTIAL — aerus_npc_sheets.md e aerus_main_npcs.md têm "initial posture" por NPC mas sem exemplo de como o GM ajusta a narração para cada faixa de reputação.
- (c) Edge cases: ❌ MISSING — sem protocolo para NPC que não sabe a reputação da party (city desconhecida), ou NPC com memória de evento específico que contradiz a reputação atual.

---

#### NPC hostil (-50 ou abaixo) — pode atacar imediatamente?

- (a) Arbitration rule: PARTIAL — aerus_mechanics_systems.md §General Effects: "Lower reputation increases surveillance, refusal of service, obstruction, and violence." reputation_gates.yaml cita "Church inquisitors are now actively tracking the player" e "Imperial soldiers in any location will challenge them on sight." Mas sem protocolo de quando a violência é imediata vs gradual.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para NPC hostil em local neutro (Port Myr), ou para party com reputação diferente por jogador.

---

#### NPC aliado (+50 ou acima) — o que ele faz espontaneamente

- (a) Arbitration rule: PARTIAL — reputation_gates.yaml define benefícios específicos por gate (militar escoltando, rota de contrabando, etc.) mas sem comportamento geral de NPC aliado fora dos gates documentados.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para NPC aliado em perigo e comportamento espontâneo de resgate.

---

#### Tentar persuadir NPC de facção inimiga

- (a) Arbitration rule: PARTIAL — aerus_mechanics_systems.md §General Effects implica dificuldade aumentada mas sem modificador de atributo ou DC específico.
- (b) Narrative example: PARTIAL — narration_bible.md §Resposta a ação social tem estrutura e exemplo (Maren Toss) mas sem contexto de facção inimiga.
- (c) Edge cases: ❌ MISSING — sem protocolo para NPC que é persuadido a trair sua facção, e consequência de reputação daí decorrente.

---

#### Revelar identidade de Viajante (Marca da Cúpula) em contexto hostil

- (a) Arbitration rule: ✅ aerus_mechanics_magic_isekai.md §How NPCs React to the Mark — tabela por região com reações específicas e linhas de diálogo de NPC.
- (b) Narrative example: ✅ aerus_mechanics_magic_isekai.md — diálogos de NPC como "Roll your sleeve up, or I will ask anyway." e "Traveler. Good. You people usually die fast or last long."
- (c) Edge cases: PARTIAL — aerus_lore_dome_factions.md §The Dome Mark descreve comportamento da Marca (não pode ser removida permanentemente, pulsa perto de Fragmentos, fica fria em locais de morte de Viajante). Mas sem protocolo para Marca pulsando durante negociação diplomática secreta, ou para tentar esconder a Marca ativamente.

---

#### Rumor sendo espalhado pelos jogadores — como rastrear

- (a) Arbitration rule: PARTIAL — CLAUDE.md menciona `rumor_manager.py` que "injects faction-biased rumor variants per player into L2 context once per rumor_id". rumors.yaml tem estrutura de base + variantes por facção. Mas sem protocolo de o que acontece quando o jogador cria um rumor novo (não listado no yaml).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para rumor verdadeiro vs falso espalhado pelos jogadores, ou rumor que contradiz canon.

---

#### Missão de uma facção que contradiz outra ativa

- (a) Arbitration rule: PARTIAL — campaign_mission_structure.md §Reputation conflict rule: "When players complete a faction mission, the GM should automatically apply a partial negative delta to antagonistic factions." aerus_mechanics_systems.md §Cross-Faction Pressure tem exemplos de ações que afetam múltiplas facções. Mas sem protocolo de como o GM narra o conflito quando o jogador tem duas missões ativas simultaneamente.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para missão onde completar o objetivo A de church_01 impossibilita o objetivo de children_01 ao mesmo tempo.

---

#### Dois jogadores com facções opostas na mesma cena de negociação

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### NPC que morre por escolha do jogador — consequência de reputação

- (a) Arbitration rule: PARTIAL — aerus_mechanics_systems.md §Typical Negative Triggers: "violence against members or institutions". aerus_npc_sheets.md §NPC Design Rules: "If an NPC matters politically, treat combat against them as campaign-shaping." Mas sem tabela de quanto cai a reputação por matar NPC por tier/importância.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para matar NPC aliado de outra facção acidentalmente, ou testemunha que viu o assassinato.

---

#### Objetivo secreto conflitando com ação do grupo

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Secret Objectives tem diretrizes de design mas sem protocolo de como o GM arbitra quando o objetivo secreto de jogador A impede o sucesso de jogador B.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### MORTE E CONSEQUÊNCIAS PERMANENTES

---

#### Morte de NPC aliado importante — protocolo narrativo

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Consequences lista "An NPC now trusts or fears the group" como padrão de consequência, e aerus_npc_sheets.md define NPCs como "campaign-shaping" se importantes. Mas sem protocolo de narração específico para morte de NPC aliado.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para Thresh morrendo antes de completar children_03, ou Maren morrendo com informação vital não revelada.

---

#### Morte de NPC que ainda tinha informação vital

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Fragmento destruído — Surge imediato raio de 200km

- (a) Arbitration rule: PARTIAL — aerus_mechanics_magic_isekai.md §Aeridian Fragments: "Destroying a Fragment releases energy equivalent to a maximum-grade Surge." Mas sem protocolo narrativo de o que acontece nos 200km de raio, nem quem sabe do evento, nem consequência de facção.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para Fragmento de Valdek IV sendo destruído (campaign_mission_arcs §Arc II).

---

#### Selagem falhada na Câmara Final — o que acontece

- (a) Arbitration rule: ❌ MISSING — campaign_mission_arcs §The Final Choice descreve 4 opções mas sem protocolo para "tentativa de selar que falha mecanicamente" (vs. "escolher não selar").
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Jogador que tenta suicidar o personagem

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Perda permanente de atributo (maldição, corrupção severa)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_races.md §Corrupted Fae: "Lose permanent vitality over long progression milestones" (Onus Entis). Mas sem protocolo geral de como o GM aplica perda permanente de atributo por corrupção.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para atributo caindo abaixo do mínimo racial, ou para recuperação de atributo perdido permanentemente.

---

#### Local destruído pelo grupo — consequência geopolítica

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Consequences: "A corrupted zone expands" e "A route becomes unsafe" como padrões. Mas sem protocolo para consequências específicas de destruição de local chave (Vel'Ossian, Port Myr Broken Square).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Segredo revelado publicamente — reação das facções envolvidas

- (a) Arbitration rule: PARTIAL — aerus_lore_geopolitics_economy.md §Recent Events descreve quem sabe o quê de cada evento, útil como modelo. aerus_mechanics_systems.md §Cross-Faction Pressure tem exemplos de ações que ativam múltiplas facções. Mas sem protocolo de como o GM aplica o "quem reage como" quando o grupo revela um segredo específico.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para segredo revelado a uma facção que não estava na lista de "quem sabe".

---

### MULTIPLAYER E COOPERAÇÃO

---

#### Dois jogadores fazendo ações simultâneas — batching de 3s

- (a) Arbitration rule: PARTIAL — CLAUDE.md descreve `action_batch_window_seconds: 3` e `game_master.py` como orquestrador de turnos. Mas sem protocolo narrativo de como o GM arbitra e narra duas ações simultâneas conflitantes (A tenta negociar enquanto B ataca).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para ações que se cancelam mutuamente.

---

#### Jogadores em locais diferentes na mesma sessão

- (a) Arbitration rule: ❌ MISSING — nenhum documento define como o GM gerencia narração paralela, quando cortar entre cenas, ou como manter tensão coerente.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para jogador A em combate enquanto jogador B está em viagem.

---

#### Um jogador morto (espectador) enquanto grupo continua

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Conflito entre jogadores (PvP) — é permitido? protocolo

- (a) Arbitration rule: PARTIAL — campaign.yaml tem `friendly_fire: false` que implica PvP desabilitado. Mas sem protocolo para "o que o GM faz quando um jogador declara intenção de atacar outro jogador."
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — sem protocolo para objetivo secreto que explicitamente pede prejudicar outro jogador.

---

#### Jogador ausente numa sessão — personagem some ou fica?

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Objetivo secreto de um jogador revelado acidentalmente

- (a) Arbitration rule: ❌ MISSING — aerus_gm_guide.md §Secret Objectives tem diretrizes gerais mas sem protocolo de como o GM arbitra o reveal acidental.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Um jogador sabota ação de outro (intencional ou não)

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Todos os jogadores falham na mesma rolagem crítica

- (a) Arbitration rule: ❌ MISSING — nenhum documento define protocolo para falha de grupo total.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### SISTEMA DE CLARIFICAÇÃO DO GM

---

#### Quando o GM deve pausar e pedir rolagem vs decidir sozinho

- (a) Arbitration rule: PARTIAL — narration_bible_kernel.md: "Se houver rolagem de dado, explicitar antes do resultado: quem rola, qual dado e o que está em jogo." Mas sem critério de quando uma ação requer rolagem vs quando é automática.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Ação impossível pelo lore — como recusar sem quebrar imersão

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Table Rules: "Be direct when the world is clear." Mas sem protocolo específico de como recusar ação impossível (voar sem magia, teletransportar para outro continente) mantendo o tom literário.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Ação que não tem regra definida — como improvisar consistentemente

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Table Rules: "Make failure productive whenever possible" e "Protect momentum." Mas sem protocolo de improvisação estruturada (similar ao "yes, and" ou ao Move trigger de Ironsworn).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Jogador tenta usar conhecimento OOC (fora do personagem)

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Ação que contradiz o lore canônico do Aerum

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Pergunta sobre mecânica que o GM não tem resposta clara

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Table Rules: "Be ambiguous only when the fiction supports ambiguity." Mas sem protocolo explícito de como o GM mascara a ausência de regra.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

---

## SEÇÃO 2 — GAPS POR COMPARAÇÃO COM SISTEMAS MADUROS

---

### Comparação com D&D 5E

| Conceito | Equivalente no Aerum | Status |
|---|---|---|
| Condições com efeitos mecânicos precisos (lista completa) | Nenhuma lista de condições existe. world_kernel.md lista backfires mas não condições de status. | ❌ MISSING — **CRÍTICO** |
| Regra de concentração para magias mantidas | Não existe. Channeler tem "Open Channel" mas sem custo de concentração definido. | ❌ MISSING — **ALTO** |
| Saving throw vs atributo específico | Não existe. Checks usam atributos mas sem framework de "saving throw" separado. | ❌ MISSING — **ALTO** |
| Advantage/Disadvantage | Não existe. Racial Onus Entis cita penalidades como "-2 on magical rolls" mas sem sistema geral. | ❌ MISSING — **ALTO** |
| Short rest vs long rest (recuperação parcial) | PARTIAL — narration_bible_kernel.md diferencia "repouso leve" de "sono seguro" mas sem valores. | PARTIAL — **ALTO** |
| Death saving throws | Não existe. Permadeath confirmado mas sem mecânica de limbo antes da morte. | ❌ MISSING — **CRÍTICO** |
| Opportunity attack | Não existe. | ❌ MISSING — **MÉDIO** |
| Flanking (bônus por posicionamento) | Não existe. | ❌ MISSING — **MÉDIO** |
| Cover (cobertura em ranged attacks) | Não existe. | ❌ MISSING — **MÉDIO** |
| Grapple e condição restrained | Não existe como condição definida. | ❌ MISSING — **MÉDIO** |
| Concentration break por dano | Não existe. | ❌ MISSING — **ALTO** |

---

### Comparação com Blades in the Dark

| Conceito | Equivalente no Aerum | Status |
|---|---|---|
| Clock de pressão | PARTIAL — campaign.yaml tem `tension_thresholds` (1-10) que afeta modelo escolhido. Mas sem relógio visual ou protocolo narrativo de progresso. | PARTIAL — **ALTO** |
| Flashback | Não existe. | ❌ MISSING — **MÉDIO** |
| Resistência (sofrer consequência menor pagando custo) | Não existe. | ❌ MISSING — **ALTO** |
| Escala de consequência (reduzida/normal/aumentada/catastrófica) | PARTIAL — aerus_gm_guide.md §Consequences tem padrões gerais mas sem escala formal. | PARTIAL — **ALTO** |
| Position e Effect (risco vs impacto antes de rolar) | Não existe. narration_bible_kernel.md pede "explicitar antes do resultado: quem rola, qual dado e o que está em jogo" mas sem framework de Position/Effect. | ❌ MISSING — **CRÍTICO** |
| Devil's Bargain | Não existe formalmente. Mas aerus_gm_guide.md §Table Rules "Let victory cost something" se aproxima. | ❌ MISSING — **ALTO** |
| Downtime actions | Não existe. Sem definição do que os personagens fazem entre sessões. | ❌ MISSING — **ALTO** |
| Heat e Wanted Level | PARTIAL — reputation_gates.yaml tem "faction_pressure" como tipo de gate (ex: inquisidores rastreando, wanted notices). Mas sem sistema numérico de calor. | PARTIAL — **MÉDIO** |
| Trauma (consequência permanente de falha grave não-morte) | Não existe formalmente. aerus_mechanics_races.md §Corrupted Fae tem "Lose permanent vitality" mas não generalizado. | ❌ MISSING — **ALTO** |

---

### Comparação com Vampire: The Masquerade

| Conceito | Equivalente no Aerum | Status |
|---|---|---|
| Conflito social com mecânica (Persuasão, Intimidação com dados) | PARTIAL — aerus_mechanics_systems.md §Faction Reputation tem faixas e aerus_main_npcs.md tem `bribe_threshold` e `disposition`, mas sem roll de persuasão/intimidação. | PARTIAL — **CRÍTICO** |
| Frenesi/perda de controle (gatilho e narrativa) | Não existe. Mencionado como conceito para Chimerics mas sem mecânica. | ❌ MISSING — **ALTO** |
| Blood pool / recurso limitado de poder | PARTIAL — MP existe nos stat blocks de NPC mas sem regras de recuperação/esgotamento para jogadores. | PARTIAL — **ALTO** |
| Masquerade (segredo dos Viajantes exposto) | PARTIAL — aerus_mechanics_magic_isekai.md §How NPCs React to the Mark tem reações regionais. aerus_lore_dome_factions.md tem "The Dome Mark cannot be permanently removed." Mas sem escala de exposição pública com consequências crescentes. | PARTIAL — **ALTO** |
| Diablerie (absorver poder de outro) | Não existe. | ❌ MISSING — **MÉDIO** |
| Compulsion (comportamento forçado por natureza) | PARTIAL — Onus Entis das raças é o equivalente mais próximo, mas sem mecânica de trigger. | PARTIAL — **MÉDIO** |
| Humanity/moralidade | Não existe. aerus_gm_guide.md tem "consequences are durable" mas sem track de moralidade. | ❌ MISSING — **MÉDIO** |

---

### Comparação com Ironsworn / Forbidden Lands

| Conceito | Equivalente no Aerum | Status |
|---|---|---|
| Move triggers (o que obriga rolagem vs o que é automático) | PARTIAL — narration_bible_kernel.md: "Se houver rolagem de dado, explicitar antes..." mas sem lista de triggers de roll. | PARTIAL — **CRÍTICO** |
| Supply como recurso narrativo (comida, tocha, etc.) | PARTIAL — items.yaml tem peso e aerus_mechanics_languages_crafting.md §Required Tools tem ferramentas, mas sem sistema de supply/depletion. | PARTIAL — **ALTO** |
| Corruption track progressivo com marcos narrativos | PARTIAL — aerus_mechanics_magic_isekai.md tem Rooting como track, world_kernel.md tem backfires. Mas sem corruption track com marcos definidos (ex: Stage 1 = visões; Stage 3 = perda de controle parcial). | PARTIAL — **CRÍTICO** |
| Oráculos (GM rola para determinar detalhes do mundo) | Não existe. rumors.yaml é o mais próximo (geração de eventos do mundo), mas sem framework de oracle rolls. | ❌ MISSING — **MÉDIO** |
| Solo vs group mechanics (diferença quando um jogador está só) | Não existe. | ❌ MISSING — **MÉDIO** |

---

---

## SEÇÃO 3 — SITUAÇÕES QUE O SLM VAI ENCONTRAR SEM RESPOSTA

As 30 perguntas mais prováveis em sessão sem resposta clara na documentação atual:

---

| # | Pergunta que o GM precisaria responder | Documento mais próximo | Prioridade |
|---|---|---|---|
| 1 | "Eu ataco com minha espada. Jogo qual dado? Qual atributo?" | aerus_base_classes.md §Blade — mas sem mecânica de ataque | **CRÍTICO** |
| 2 | "Quantos HP perco com esse ataque?" | Stat blocks de NPCs em aerus_main_npcs.md têm HP mas sem fórmula de dano para players | **CRÍTICO** |
| 3 | "Meu personagem tem 0 HP. Estou morto ou posso ser estabilizado?" | campaign.yaml `permadeath: true` + aerus_mechanics_magic_isekai.md "Death is real death" mas sem limiar | **CRÍTICO** |
| 4 | "Qual dado eu rolo para resistir a uma condição (veneno, atordoamento)?" | Nenhum | **CRÍTICO** |
| 5 | "Eu casto um feitiço de nível 3 em zona corrompida. Qual a chance de backfire?" | world_kernel.md lista tipos mas sem probabilidade por zona/nível | **CRÍTICO** |
| 6 | "Quanto XP ganha por matar um inimigo Tier 2?" | narration_bible_kernel.md menciona XP por ações impactantes mas sem tabela | **CRÍTICO** |
| 7 | "Quero fugir do combate. O que rolo e qual o custo?" | Nenhum | **CRÍTICO** |
| 8 | "Eu estou envenenado. Quando o efeito termina e como narro isso?" | Nenhum — lista de condições não existe | **CRÍTICO** |
| 9 | "Dois jogadores usam feitiços diferentes no mesmo turno. Qual eu resolvo primeiro?" | CLAUDE.md descreve batching de 3s mas sem arbitration narrativa | **CRÍTICO** |
| 10 | "Consigo negociar preço com esse comerciante? Qual atributo rolo?" | aerus_lore_geopolitics_economy.md tem preços mas sem mecânica de barganha | **CRÍTICO** |
| 11 | "Meu personagem descansou numa taverna. Quanto HP recupero?" | narration_bible_kernel.md fala de descanso seguro sem números | **ALTO** |
| 12 | "Eu quero fazer craft de Minor Stability Amulet numa zona T3. É possível? Qual o modificador?" | aerus_mechanics_languages_crafting.md tem DC mas sem penalidade de zona | **ALTO** |
| 13 | "O boss chegou a 50% de HP. Qual o gatilho da fase 2?" | aerus_gm_guide.md §Boss Phase Change tem exemplo de narração mas sem gatilho numérico | **ALTO** |
| 14 | "Estou com reputação -51 na Igreja. O inquisidor que encontrei me ataca imediatamente?" | reputation_gates.yaml cita rastreamento e "confrontar à vista" para soldados imperiais mas sem regra geral | **ALTO** |
| 15 | "Meu aliado NPC foi controlado mentalmente e está me atacando. Como funciona o combate?" | Nenhum | **ALTO** |
| 16 | "Jogador B está a 500km de distância numa viagem enquanto Jogador A está em combate. Narro as duas cenas?" | Nenhum | **ALTO** |
| 17 | "Meu personagem falhou em 3 tentativas de magia consecutivas. Ele acumulou corrupção?" | world_kernel.md lista backfires mas sem track acumulativo | **ALTO** |
| 18 | "Qual atributo uso para intimidar o guarda da fronteira?" | Nenhum — sem mapeamento explícito ação social → atributo | **ALTO** |
| 19 | "Minha mutação de nível 25 foi desbloqueada durante o combate. Eu recebo agora ou depois?" | aerus_class_mutations.md descreve outcomes mas sem timing | **ALTO** |
| 20 | "Eu estou no Cinturão Pálido (Void Zone). Posso usar magia normalmente?" | aerus_lore_geography.md menciona "permanent fog" mas sem regra de magic in Void Zone | **ALTO** |
| 21 | "O jogador quer comprar Keth Grade 2 em Port Myr. É ilegal. O que acontece se for pego?" | aerus_lore_geopolitics_economy.md §Keth Gray Market cita riscos genéricos mas sem protocolo de flagrante | **ALTO** |
| 22 | "Um jogador tentou suicidar o personagem. O que o GM faz?" | Nenhum | **ALTO** |
| 23 | "O Fragmento Aeridiano de Valdek IV foi destruído pela party. O que acontece nos próximos 5 minutos narrativos?" | campaign_mission_arcs §Arc II menciona o evento mas sem protocolo imediato | **ALTO** |
| 24 | "O jogador usa conhecimento OOC ('eu sei que o Weaver está na Pale Belt porque li a ficha'). Como o GM arbitra?" | Nenhum | **ALTO** |
| 25 | "Meu personagem atacou e matou Thresh. Qual a penalidade de reputação exata com os Children?" | aerus_mechanics_systems.md §Typical Negative Triggers: "violence against members" mas sem delta específico | **MÉDIO** |
| 26 | "Estamos acampando no wilderness. Quantas horas de guarda são necessárias para prevenir emboscada?" | Nenhum | **MÉDIO** |
| 27 | "Vel'Arath — meu personagem Mist Elf tenta entrar. O bosque permite automaticamente?" | aerus_travel.md: "The forest decides who may enter" mas sem critério por raça | **MÉDIO** |
| 28 | "O jogador quer criar um rumor falso sobre o Empire em Port Myr. Como rastrear o efeito?" | rumors.yaml tem sistema de rumores mas sem protocolo para rumor criado pelo jogador | **MÉDIO** |
| 29 | "Dois jogadores têm reputações opostas com a Igreja. Um está em +60, outro em -55. Como o NPC reage à party?" | Nenhum — sem protocolo de reputação coletiva vs individual | **MÉDIO** |
| 30 | "O jogador usa o atributo LUK para tentar algo. Qual o DC base e quando LUK é o atributo certo?" | aerus_mechanics_races.md menciona LUK mas sem framework de quando usar cada atributo | **MÉDIO** |

---

---

## SEÇÃO 4 — O QUE DOCUMENTAR ANTES DO FINE-TUNE

---

### CRÍTICO (sem isso o modelo quebra a sessão)

- **`aerus_combat_core.md`** — Mecânica completa de combate: dado de ataque por classe, fórmula de dano base, iniciativa (atributo + dado), defesa (DEX + armadura), HP/0HP/morte. Sem isso o modelo inventa regras inconsistentes em cada sessão.

- **`aerus_conditions_list.md`** — Lista completa de condições de status (envenenado, atordoado, amedrontado, corrompido, imobilizado, etc.) com: duração padrão, efeito mecânico, como aplicar, como remover, e 1-2 frases de narração para cada.

- **`aerus_corruption_track.md`** — Corruption track progressivo com 4-5 estágios numerados: limiar de acumulação (ex: 3 falhas de magia = Stage 1), efeito mecânico por estágio, sinal narrativo por estágio, como remover cada estágio. Inclui interação com Keth e Fragmentos.

- **`aerus_roll_triggers.md`** — Mapa de quando o GM pede rolagem vs quando a ação é automática. Inclui: qual atributo por tipo de ação (combate, social, exploração, craft, magia), o que é stake em cada roll, o que distingue sucesso de sucesso parcial de falha.

- **`aerus_death_protocol.md`** — Protocolo completo de morte: limiar de 0 HP, "death window" (existe ou não?), permadeath imediata vs estabilização, transição para espectador, quando criar novo personagem, narração obrigatória de morte.

- **`aerus_magic_resolution.md`** — Framework de resolução mágica: dado de spell, atributo base (INT para elementais, CAR para Spirit), DC por nível de magia (1-10), tabela de backfire por zona (normal/corrompida/Fragmento próximo/Void Zone), spell failure parcial vs total vs backfire.

- **`aerus_xp_table.md`** — Tabela de XP por tipo de ação: combate por tier, objetivo de missão por tipo, diplomacia bem-sucedida, craft, descoberta de lore. Limiar de XP por nível (ou framework de milestone). Protocolo de quando o GM anuncia e narra o level up.

---

### ALTO (sem isso o modelo improvisa errado)

- **`aerus_social_mechanics.md`** — Mecânica de interação social: atributo para persuasão (CAR), intimidação (STR ou CAR), engano (DEX ou INT), DC base por disposição de NPC, modificadores de reputação por faixa, resultado de sucesso parcial em negociação. Exemplos narrativos por tipo de resultado.

- **`aerus_rest_recovery.md`** — Tabela de recuperação por tipo de descanso: repouso leve (1-2h), sono seguro (6-8h), sono em zona corrupta, descanso com cura mágica. Valores de HP e MP recuperados. Protocolo de descanso interrompido por emboscada.

- **`aerus_flee_surrender.md`** — Mecânica de fuga de combate (quando possível, roll de DEX vs inimigo, custo narrativo) e rendição de inimigo (o que acontece, como o GM narra, o que o jogador pode fazer com prisioneiro).

- **`aerus_crafting_failure.md`** — O que acontece em falha de craft: falha por 1-4 (ingrediente principal perdido), falha por 5+ (todos ingredientes + dano ao artesão), falha crítica (acidente com efeito de backfire). Exemplos narrativos de cada nível.

- **`aerus_multiplayer_protocol.md`** — Como o GM gerencia: ações simultâneas conflitantes (batch de 3s), jogadores em locais diferentes na mesma sessão, espectador após morte, ausência de jogador, objetivo secreto revelado acidentalmente, sabotagem entre jogadores.

- **`aerus_npc_kill_consequences.md`** — Tabela de consequência por tipo de NPC morto: NPC de rua (delta leve), agente de facção (delta moderado por facção), NPC chave com missão ativa (missão cancelada + delta pesado), NPC com informação vital (informação perdida → protocolo de workaround). Exemplos por cada facção.

- **`aerus_surge_protocol.md`** — Protocolo completo de Surge: raio por nível (1-10 de magia), efeitos narrativos por estágio, quem sabe/sente no mundo, consequência de facção após Surge público, diferença entre Surge normal e Surge por Fragmento destruído.

- **`aerus_attribute_guide.md`** — Quando usar cada atributo (STR, DEX, INT, VIT, LUK, CAR) como base de roll em situações comuns. Inclui casos de LUK como atributo de roll e CAR para social. Essencial para consistência do GM.

- **`aerus_faction_conflict_arbitration.md`** — Protocolo para: missões conflitantes simultâneas, dois jogadores com facções opostas na mesma cena, NPC que conhece um jogador como aliado e outro como inimigo, reputação individual vs coletiva da party.

- **`aerus_combat_special_terrain.md`** — Modificadores mecânicos e narrativos para: zona corrupta (penalidade de magia), Ondrek Pass (magia bloqueada), Vel'Arath (magia instável/antiga), Heart of Ashes (zona T4-5), água (penalidade STR/DEX), altitude (penalidade VIT).

---

### MÉDIO (sem isso o modelo fica genérico)

- **`aerus_downtime.md`** — O que os personagens podem fazer entre sessões: treino de linguagem (sessões necessárias por idioma já documentadas), aprendizado de magia, recuperação de atributo permanente, crafting sem urgência, gestão de reputação.

- **`aerus_boss_design.md`** — Protocolo de boss fights: quando usar phase change (limiar de HP sugerido: 50%, 25%), o que muda na fase 2 (novos ataques, mobilidade, aura de corrupção), como narrar cada transição, quem pode ter múltiplas fases.

- **`aerus_ooc_handling.md`** — Como o GM recusa ações OOC sem quebrar imersão: ação impossível pelo lore (recusa com âncora narrativa), conhecimento OOC usado pelo jogador (diferença entre "meu personagem saberia disso?" e "eu sei isso"), ação que contradiz canon (como o mundo reage naturalmente).

- **`aerus_travel_narrative.md`** — Exemplos narrativos por tipo de encounter de viagem: how to narrate each encounter type from travel.yaml (bandits, merchants, lesser leviathan, ghost ship, avalanche, etc.). Inclui exemplos de clima extremo e chegada a locais especiais.

- **`aerus_void_zone_rules.md`** — Regras específicas de Void Zone (Pale Belt, Red Sea, Limen Vel'Arath): efeito em magia, navegação, saúde de personagens, quanto tempo alguém pode aguentar, interação com raça Khorathi (Body Without Thread).

- **`aerus_rumor_injection.md`** — Como o GM cria e rastreia rumores gerados pelos jogadores: formato, como afeta NPCs e facções, diferença entre rumor verdadeiro/falso espalhado, como o GM pode usar rumor de player como hook.

- **`aerus_vel_arath_entry.md`** — Critérios de entrada em Vel'Arath: quem o bosque admite (por raça, por histórico de ação, por intenção), o que acontece quando um membro é recusado, o que acontece dentro do bosque (tempo distorcido, efeito da Marca, magia do Fio antigo).

- **`aerus_morality_track.md`** — Track simples de moralidade/humanidade para o Aerum: ações que movem para cima/baixo, marcadores narrativos visíveis por faixa, consequência de faixa baixa (NPCs distantes, Marca reage diferente, facções desconfiam). Não precisa ser tão complexo quanto VtM.

- **`aerus_leveling_narration.md`** — Protocolo narrativo completo de level up: quando interromper a cena, frases padrão do GM, como narrar mutação formal em cada classe (exemplos por Blade, Sorcerer, Channeler), como apresentar escolha de path ao jogador.

---

> FIM DO DOCUMENTO
> Total de gaps identificados: ~130 itens (Seção 1) + 25 itens (Seção 2) + 30 situações (Seção 3)
> Prioridade total de documentos a criar: 7 CRÍTICO + 10 ALTO + 9 MÉDIO = 26 documentos
