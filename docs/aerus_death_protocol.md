# Aerus RPG — Death Protocol

> Protocolo de morte, queda a 0 HP, death saves, feridas permanentes e espectador.
> Documento criado para fechar gaps CRÍTICOS identificados no GAP_ANALYSIS_NARRATOR.md.

---

## 1. Limiar de Queda — 0 HP

Quando um personagem sofre dano suficiente para reduzir seus HP a **0 ou abaixo**:

1. O personagem **cai** — incapacitado, inconsciente.
2. Começa a **contagem de morte**: o personagem morre em **3 turnos** se não receber ajuda.
3. Durante esses 3 turnos, o personagem não pode agir, falar ou usar itens.

**Morte Imediata por Dano Massivo:**
Se o dano sofrido em uma única ação for igual ou maior que **2× os HP máximos** do personagem, a morte é **imediata** — sem contagem, sem death saves. O GM narra a extinção do personagem abruptamente.

---

## 2. Death Saves — Resistindo à Morte

Enquanto está na contagem de 3 turnos, o personagem realiza um **death save** no início de cada um de seus turnos (mesmo incapacitado — é um reflexo de sobrevivência):

```
Death Save = d20 + Modificador de CON + Modificador de VIT (vontade de viver)
```

**DC base:** 10 + (número de vezes que o personagem já caiu a 0 HP nessa campanha × 2)

> Exemplo: primeira queda = DC 10. Segunda queda = DC 12. Quinta queda = DC 18.

| Resultado | Efeito |
|-----------|--------|
| Falha Crítica (natural 1 ou ≤ DC − 6) | Morre neste turno (não espera os 3 turnos) |
| Falha | Perde 1 turno da contagem (sem efeito extra) |
| Neutro | Mantém estado; contagem continua normalmente |
| Sucesso | Ganha +1 turno extra antes de morrer (conta regressiva pausa por 1 turno) |
| Sucesso Crítico (natural 20) | Recupera 1 HP, sai do estado de queda — mas com ferida permanente |

**Importante:** o death save **não estabiliza** o personagem. Ele apenas retarda ou acelera a morte. A estabilização real exige intervenção ativa de outro personagem.

---

## 3. Estabilização por Aliado

Outro personagem pode tentar estabilizar o caído usando:

| Método | Ação | Resultado |
|--------|------|-----------|
| Primeiros socorros (VIT/STR check DC 12) | 1 ação completa | Estabiliza — pausa a contagem; personagem permanece inconsciente com 1 HP |
| Magia de cura (qualquer nível) | 1 ação | Restaura os HP conjurados; personagem volta consciente |
| Item de cura (poção, elixir) | 1 ação (usar em aliado) | Restaura os HP do item; personagem volta consciente |

Usar item consumível em combate consome **1 ação completa** do turno do personagem que administra — não é ação livre.

---

## 4. Feridas Permanentes

Ao ser estabilizado ou sobreviver via death save crítico, o personagem sofre **feridas permanentes** cuja gravidade depende do dano que causou a queda:

| Dano da queda vs HP máximo | Gravidade da Ferida |
|---|---|
| 50–74% do HP máximo | **Ferida Leve** — narrativa apenas (cicatriz, dor residual); sem penalidade mecânica |
| 75–99% do HP máximo | **Ferida Grave** — penalidade de −2 em um atributo relevante (GM escolhe baseado no tipo de dano); dura até tratamento adequado |
| 100–149% do HP máximo (sem morte imediata) | **Ferida Severa** — penalidade de −4 em atributo + condição persistente (ex: Membro Fraturado, Visão Comprometida); dura até cura formal |
| ≥ 150% do HP máximo (sem morte imediata por ser ≥2× o máximo seria morte, portanto este nível é por dano acumulado no turno) | **Ferida Crítica** — penalidade de −6 em atributo + condição persistente grave; pode ser permanente sem tratamento divino |

### 4.1 Cura de Feridas Permanentes

| Gravidade | Tratamento necessário |
|-----------|----------------------|
| Leve | Descanso longo (recuperação natural) |
| Grave | Médico especializado ou magia de cura de nível ≥ 3 + descanso |
| Severa | Magia de cura de nível ≥ 6 ou item raro de recuperação (ex: Lágrima de Aer) |
| Crítica | Magia divina de nível maior que o grau da ferida, ou avatar direto de uma divindade |

---

## 5. Morte Permanente — Protocolo Narrativo

Quando a morte é confirmada (contagem esgotada, death save falha crítica, ou dano massivo):

1. **O GM narra a morte sem heroísmo obrigatório.** A morte no Aerum é abrupta e real. Não há monólogo final, a menos que o contexto narrativo justifique claramente (personagem rodeado de aliados, morte lenta por envenenamento, etc.).
2. **Não pausar a cena imediatamente.** O GM pode concluir a ação em andamento (inimigo atual sendo derrotado, negociação terminando) antes de chamar atenção plena para a morte.
3. **Anunciar claramente** ao grupo que o personagem morreu — sem ambiguidade.
4. **Consequências narrativas imediatas:** reação dos outros personagens (NPCs e jogadores), impacto na missão ativa, objetos do personagem morto.

### 5.1 Referência de Voz (do aerus_gm_guide.md)

> *"There is no heroic final monologue, only the abrupt violence of a life interrupted. The party has one turn to react before the narrative moves forward."*

---

## 6. Espectador — Protocolo Pós-Morte

Após a confirmação da morte:

1. O **jogador permanece presente** na sessão e pode ver toda a cena continuando.
2. O jogador **não interfere narrativamente** — o personagem morto não fala, não age, não aparece como fantasma (a menos que um evento de lore específico justifique).
3. **Criação do novo personagem:** o jogador pode criar seu próximo personagem assim que a **cena atual** for encerrada ou assim que a **sessão** terminar — o que vier primeiro.
4. O novo personagem entra na narrativa na próxima cena com justificativa plausível (novo Viajante convocado, aliado que apareceu, etc.).

**Objetivo secreto ainda ativo:** se o personagem morto possuía um objetivo secreto incompleto, o GM arquiva silenciosamente o objetivo. Pode reintroduzir como gancho para o novo personagem ou para outro jogador, a critério narrativo.

**Informação vital que só o personagem morto sabia:** o GM deve ter registrado essa informação em estado. Pode ser revelada por: documentos que o personagem carregava, memória de NPC, ou recuperação mágica de memória (custo narrativo alto).

---

## 7. Jogador Ausente

Se um jogador não está presente na sessão, o personagem **desaparece narrativamente** — dorme, fica de guarda, ficou para trás na última parada. O GM não controla o personagem como NPC. O personagem reaparece na próxima sessão sem penalidade mecânica, com justificativa narrativa mínima.

---

## 8. Resumo Rápido para o GM

```
Dano ≥ 2× HP máx → Morte imediata
Dano reduz HP a 0  → Contagem de 3 turnos começa
                   → Death save por turno (CON + VIT vs DC escalante)
                   → Aliado pode estabilizar (primeiros socorros / cura / item)
Sobreviveu        → Ferida permanente (gravidade proporcional ao dano)
Não foi estabilizado no tempo → Morte permanente
```
