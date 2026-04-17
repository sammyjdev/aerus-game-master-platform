# Aerus RPG — Magic Resolution

> Sistema de mana, níveis de magia, backfire, falha de feitiço e Surge.
> Documento criado para fechar gaps CRÍTICOS identificados no GAP_ANALYSIS_NARRATOR.md.

---

## 1. Pool de Mana

### 1.1 Mana Máxima

```
Mana Máxima = Modificador Mágico × Nível × Proficiência Mágica
```

Onde:
- **Modificador Mágico** = valor do atributo primário de magia ÷ 5 (arredondado para baixo)
  - Magia elemental → INT ÷ 5
  - Magia espiritual/social → CAR ÷ 5
  - Magia híbrida → (INT + CAR) ÷ 10
- **Nível** = nível atual do personagem (1–100)
- **Proficiência Mágica** = proficiência no elemento ou escola utilizada (1–20)

> **Exemplo:** Nível 20, INT 40 (mod 8), proficiência de fogo 6 → Mana Máxima = 8 × 20 × 6 = **960**

*Nota: valores exatos serão calibrados em playtest. A fórmula acima fornece a escala de referência.*

### 1.2 Recuperação de Mana

| Tipo de descanso | Recuperação |
|---|---|
| Descanso curto (1 hora de repouso) | 25% da Mana Máxima |
| Descanso longo (8 horas de sono) | 100% da Mana Máxima |
| Por turno em combate (recuperação passiva) | Modificador Mágico × 2 por turno |
| Meditação ativa (ação completa fora de combate) | Modificador Mágico × Proficiência Mágica por minuto |
| Fragmento Aeridiano a ≤50m | Recuperação passiva dobrada; sem risco de backfire |

---

## 2. Níveis de Magia e Custo de Mana

Cada feitiço tem um nível (1–10). O custo de mana escala exponencialmente:

| Nível do Feitiço | Custo de Mana Base | Restrição de Acesso |
|---|---|---|
| 1 | 1 | Disponível desde o nível 1 |
| 2 | 3 | Nível 5+ do personagem |
| 3 | 7 | Nível 10+ |
| 4 | 15 | Nível 20+ |
| 5 | 31 | Nível 30+ |
| 6 | 63 | Nível 45+ |
| 7 | 127 | Nível 60+ |
| 8 | 255 | Nível 75+ |
| 9 | 511 | Nível 90+ |
| 10 | 1023 | Nível 100 apenas |

O custo base pode ser **reduzido** pela proficiência no elemento: cada ponto de proficiência acima do mínimo necessário reduz o custo em 5%.

---

## 3. Conjuração Sem Mana Suficiente

Se o personagem tentar conjurar um feitiço sem mana suficiente:

1. **É possível — mas o custo recai no corpo.**
2. A diferença de mana faltante é convertida em:
   - **Stamina** consumida (proporção 1:2 — 1 mana faltante = 2 pontos de stamina)
   - Se a stamina esgotar, a diferença restante sai dos **HP** (proporção 1:1)
3. **O DC de backfire aumenta drasticamente** quando conjurado sem mana (ver Seção 5).

---

## 4. Proficiência Elemental

A proficiência em um elemento ou escola mágica é uma escala separada de 1 a 20, independente do nível do personagem. Ela cresce com uso e treinamento.

| Proficiência | Acesso de Fusão |
|---|---|
| 3 em dois elementos | Fusões de Rank 1 (Gelo, Magma) |
| 5 em dois elementos | Fusões de Rank 2 (Gelo Avançado, Magma Avançado) |
| 20 em todos os cinco elementos | Caos Primordial |

---

## 5. Backfire — DC e Fatores

O backfire ocorre quando o personagem falha em uma **Verificação de Conjuração**:

```
Verificação de Conjuração = d20 + Modificador Mágico + Proficiência Elemental
```

O **DC de Backfire** é variável e calculado pelo GM com base nos seguintes fatores:

| Fator | Modificação no DC |
|---|---|
| Zona de corrupção T1 | +2 |
| Zona de corrupção T2 | +4 |
| Zona de corrupção T3 | +7 |
| Zona de corrupção T4 | +11 |
| Zona de corrupção T5 | +16 |
| Mana abaixo de 25% da máxima | +3 |
| Mana zerada (conjurando com stamina/HP) | +8 |
| HP abaixo de 30% | +3 |
| Ferida Grave ou Severa ativa | +4 |
| Elemento fora da proficiência primária | +2 |
| Estágio de Corrupção Mágica 3+ | +5 |
| Keth Grade 1 equipado | −3 |
| Keth Grade 2 equipado | −6 |
| Keth Grade 3 equipado | −10 |
| Keth Grade 4 equipado | −15 |
| Fragmento Aeridiano a ≤50m | DC de backfire anulado |

**DC base:** 10 + nível do feitiço

> Exemplo: Nível 3 de feitiço em zona T3, sem Keth, com HP baixo → DC = 10 + 3 + 7 + 3 = **DC 23**

---

## 6. Resultados de Conjuração — Escala de 5 Graus

| Resultado | O que acontece |
|---|---|
| **Falha Crítica** | Backfire total — efeito reverso ou catastrófico (ver Tabela de Backfire) |
| **Falha** | Feitiço não funciona; mana é consumida normalmente |
| **Neutro** | Feitiço funciona com efeito mínimo (metade do dano ou duração reduzida a 1 turno) |
| **Sucesso** | Feitiço funciona normalmente |
| **Sucesso Crítico** | Feitiço funciona com efeito aumentado (+50% dano/duração OU efeito narrativo adicional) |

### 6.1 Falha Parcial vs Total

- **Falha total** (Falha no d20): o feitiço não produz efeito. A mana ainda é consumida.
- **Falha parcial** (Neutro): o feitiço produz metade do efeito ou com duração reduzida. O GM escolhe o que faz sentido narrativamente.
- **Backfire** (Falha Crítica): o feitiço produz um efeito negativo conforme a tabela abaixo.

---

## 7. Tabela de Backfire por Elemento

| Elemento | Efeito de Backfire |
|---|---|
| Fogo | Queima o conjurador (dano equivalente ao feitiço, voltado para si) |
| Água | Necrose no ponto de contato (ferida progressiva, equivalente a Ferida Grave) |
| Terra | Erosão da consciência (desvantagem em todas as ações por 1d4 turnos) |
| Ar | Atrai um Eco (entidade do Fio que persegue o conjurador por 1d6 horas) |
| Energia | Causa um Surge localizado (veja Seção 8) |
| Espírito | Desperta algo próximo (GM determina: criatura dormente, espírito hostil, memória do Fio) |
| Fusão elemental | Efeito combinado dos dois elementos envolvidos |

---

## 8. Surge

Um **Surge** é uma liberação descontrolada de energia do Fio Primordial. É sempre GM-driven — não há tabela de probabilidade automática. O GM decide quando um Surge ocorre com base na narrativa.

### 8.1 Gatilhos Possíveis

- Backfire de elemento Energia em nível alto (sugestão: Tier 5+)
- Destruição de um Fragmento Aeridiano (Surge máximo automático, raio 200km)
- Conjurador em Estágio de Corrupção 4 ou 5 usando magia ofensiva poderosa
- Ritual de selagem falhado na Câmara Final
- Acúmulo de falhas mágicas repetidas no mesmo local (a critério narrativo do GM)

### 8.2 Escala de Surge

| Escala | Raio aproximado | Efeito |
|---|---|---|
| Micro | Sala / área imediata | Instabilidade mágica por 1d4 turnos; dano leve a conjuradores presentes |
| Local | Bairro / vale | Todos os feitiços nível 4+ sofrem desvantagem; criaturas corruptas são atraídas |
| Regional | Cidade / floresta | Magia instável por horas; efeitos de corrupção visíveis; NPCs em pânico |
| Máximo | 200km | Destruição de estruturas mágicas; Surto de corrupção em zonas T1-T3; sinal visível a longas distâncias |

### 8.3 Narração de Surge

O GM narra o Surge como pressão crescente antes do pico — personagens sentem o Fio se contraindo, animais fogem, Marcas da Cúpula pulsam intensamente. O pico é abrupto.

---

## 9. Dois Feitiços Simultâneos no Mesmo Alvo

Quando dois jogadores conjuram feitiços diferentes no mesmo alvo no mesmo turno:

- Cada feitiço rola sua própria Verificação de Conjuração separadamente.
- Os efeitos se aplicam em sequência (ordem de iniciativa).
- **Fusão não intencional:** se os dois feitiços são de elementos que possuem fusão conhecida (ex: fogo + ar → tempestade de chamas), e ambos acertam, o GM pode narrar o efeito combinado — trata como um feitiço de fusão do nível médio dos dois.
- **Conflito elemental** (ex: fogo + água): os efeitos se cancelam parcialmente — cada um sofre 50% de redução de efeito.

---

## 10. Canal Aberto — Regras para Canalizador

A classe Canalizador possui a habilidade "Open Channel" que alinha temporariamente o conjurador a uma fonte de poder.

- **Ativação:** ação completa; declara o elemento e a intensidade (nível 1–5 do canal).
- **Bônus:** feitiços do elemento canalizado custam 50% menos mana e ganham +2 na Verificação de Conjuração.
- **Risco:** a cada turno com canal aberto, o GM rola 1d6 em segredo:
  - 1–2: nenhum efeito
  - 3–4: DC de backfire aumenta em +3 enquanto o canal permanecer aberto
  - 5: Surge Micro localizado
  - 6: canal se rompe — Falha Crítica automática no próximo feitiço
- Canal aberto em zona de corrupção T3+: o d6 é rolado a cada ação (não só por turno).
- Manter canal aberto por mais turnos que o Nível de Proficiência do elemento: risco dobrado (rola 2d6, usa o maior).
