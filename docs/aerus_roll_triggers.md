# Aerus RPG — Roll Triggers

> Quando pedir rolagem, quando não pedir, e como mapear resultados.
> Documento criado para fechar gaps CRÍTICOS identificados no GAP_ANALYSIS_NARRATOR.md.

---

## 1. Princípio Central

**Apenas acione uma rolagem quando o resultado for variável E a falha for narrativamente interessante.**

Se não há como falhar, não role. Se a falha não muda nada na história, não role. Rolar por hábito dilui a tensão. Rolar nos momentos certos aumenta o peso de cada dado.

---

## 2. Quando NÃO Rolar

| Situação | Razão |
|---|---|
| Personagem competente executando tarefa trivial | A competência já garante o resultado |
| Total de modificadores fixos excede o DC sem rolar | Passe automático — narrar como dado |
| Tarefa onde falha não tem consequência narrativa | Rolar seria teatral, não funcional |
| Ação impossível pelo lore | Recusar sem rolagem (ver Seção 5) |
| Ação com resultado predeterminado pela narrativa | O mundo já decidiu — narrar diretamente |

**Exemplos de passe automático:**
- Viajante de nível 40 escalando uma parede comum (sem terreno adverso)
- Personagem com INT 80 lembrando de informação sobre sua área de expertise
- Guerreiro de nível 20 preparando sua arma antes do combate

---

## 3. Quando Rolar

Role quando **todas** as condições forem verdadeiras:

1. **Resultado incerto:** existe chance real de falha e de sucesso dado o perfil do personagem
2. **Falha tem consequência:** falhar muda algo na narrativa (combate piora, NPC desconfia, tempo é perdido, recurso é desperdiçado)
3. **Ação é ativa:** o personagem está fazendo algo, não apenas existindo

**Exemplos obrigatórios de rolagem:**
- Qualquer ataque em combate
- Qualquer conjuração em zona de corrupção
- Persuasão de NPC com interesses opostos
- Furtividade contra inimigo em alerta
- Primeiros socorros em personagem caído
- Crafting de item acima do nível trivial
- Death save

---

## 4. Escala de Resultado — 5 Graus

Todo resultado de rolagem é interpretado nesta escala:

```
Margem = (d20 + modificadores) − DC
```

| Grau | Margem | Descrição |
|---|---|---|
| **Falha Crítica** | Natural 1, ou ≤ −6 | Falha com complicação séria adicional |
| **Falha** | −1 a −5 | Não funciona; custo padrão |
| **Neutro** | 0 (exatamente no DC) | Funciona parcialmente, ou o GM decide com base no contexto |
| **Sucesso** | +1 a +5 | Funciona como esperado |
| **Sucesso Crítico** | Natural 20, ou ≥ +6 | Funciona com benefício adicional |

**Natural 1** é sempre Falha Crítica, independente de modificadores.
**Natural 20** é sempre Sucesso Crítico, independente do DC.

### 4.1 O que significa cada grau em contextos comuns

| Contexto | Falha Crítica | Falha | Neutro | Sucesso | Sucesso Crítico |
|---|---|---|---|---|---|
| Ataque físico | Expõe flanco, ação desperdiçada | Erra | Acerta mas não causa dano pleno | Acerta, dano normal | Crítico: dano dobrado + efeito narrativo |
| Conjuração | Backfire (tabela de elemento) | Feitiço falha, mana consumida | Efeito reduzido (metade) | Efeito normal | Efeito +50% ou bônus narrativo |
| Persuasão social | NPC hostiliza, situação piora | NPC recusa, posição firme | NPC pondera, pede mais | NPC aceita | NPC aceita e adiciona algo favorável |
| Furtividade | Detectado, inimigo em alerta máximo | Detectado, inimigo investiga | Não detectado, mas algo chamou atenção | Não detectado | Não detectado + vantagem no próximo roll |
| Primeiros socorros | Causa dano adicional ao caído (1d4) | Falha, contagem continua | Estabiliza parcialmente (+1 turno extra) | Estabiliza com sucesso | Estabiliza + recupera 1d4 HP |

---

## 5. DC de Referência por Dificuldade

| Dificuldade | DC | Contexto típico |
|---|---|---|
| Trivial | 5 | Tarefa que qualquer pessoa faria com cuidado |
| Fácil | 8 | Tarefa acessível para personagem treinado |
| Médio | 12 | Padrão — desafio real para personagem competente |
| Difícil | 16 | Requer especialização ou condições favoráveis |
| Muito Difícil | 20 | Margem de erro mínima |
| Extremo | 25 | Exige maestria e/ou circunstâncias excepcionais |
| Quase Impossível | 30 | Limiar do que é humanamente possível |

---

## 6. Ação Impossível — Como Recusar Sem Quebrar a Imersão

Quando um jogador declara uma ação que contradiz o lore ou é mecanicamente impossível, **não peça rolagem**. Rolagem implica que o resultado é variável — aqui não é.

**Protocolo:**
1. O GM faz a recusa através da ficção — o mundo responde, não o sistema.
2. Nunca dizer "isso não é permitido" — sempre narrar por que o mundo não responde como o jogador espera.
3. Oferecer uma alternativa relacionada quando possível.

**Exemplos:**

| Ação impossível | Resposta narrativa |
|---|---|
| "Destruo o Fragmento Aeridiano com meu punho" | *"Sua mão encontra resistência que não é física — o Fragmento simplesmente não cede. É como tentar machucar a ideia de pedra, não a pedra em si."* |
| "Convenço o inimigo a nos deixar passar com um d20" | Se o contexto tornar isso narrativamente plausível, rola. Se for um fã absoluto de Vor'Athek: *"Essa pessoa não está negociando. Nem o mais elaborado argumento vai funcionar aqui."* |
| "Uso magia de cura em mim mesmo" | Se a regra de backfire de Fio se aplica: *"A cura toca o Fio corrompido antes de chegar até você. A sensação não é de alívio."* → rolagem de backfire, não de cura |

---

## 7. Ação Sem Regra Definida — Como Improvisar

Quando um jogador declara algo criativo que não tem precedente nos documentos:

1. **Identifique o atributo mais relevante** (STR para força bruta, DEX para precisão, INT para raciocínio, CAR para influência, VIT para resistência, LUK para sorte/timing)
2. **Estime o DC** com base na dificuldade narrativa (tabela da Seção 5)
3. **Declare antes de rolar** qual é o atributo e o DC — transparência mantém a confiança do jogador
4. **Registre internamente** para consistência futura na mesma campanha

**Exemplo:**
> Jogador: *"Quero usar o peso do meu escudo para desviar o projétil mágico."*
> GM: *"Isso seria DEX + seu modificador de escudo, DC 16 — é um timing muito preciso."*

---

## 8. Jogador Usando Conhecimento OOC (Out of Character)

Quando um jogador usa informação que o personagem não poderia saber:

1. **Não pedir rolagem** baseada nessa informação — o resultado de uma ação não pode depender de algo o personagem não conhece.
2. **Reconhecer sutilmente** na ficção: *"[Personagem] não teria como saber isso ainda."*
3. **Se o jogador insistir:** *"Seu personagem pode tentar, mas a ação vai ser narrada como tentativa às cegas — sem o contexto que você tem como jogador."* → Desvantagem na rolagem ou DC aumentado.

---

## 9. Resumo — Árvore de Decisão do GM

```
Jogador declara ação
        ↓
É narrativamente possível?
  NÃO → Recusar através da ficção (Seção 6)
  SIM ↓
Resultado é incerto?
  NÃO → Passe automático ou falha garantida — narrar diretamente
  SIM ↓
Falha tem consequência narrativa interessante?
  NÃO → Passe automático se faz sentido; ou simplesmente narrar
  SIM ↓
→ ROLAR
  Identificar atributo + DC
  Aplicar vantagem/desvantagem se aplicável
  Interpretar resultado na escala de 5 graus
```
