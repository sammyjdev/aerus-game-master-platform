# Aerus RPG — Combat Core

> Regras de arbitragem de combate para o GM narrador.
> Documento criado para fechar gaps CRÍTICOS identificados no GAP_ANALYSIS_NARRATOR.md.

---

## 1. Dado Base de Resolução

O Aerum usa **d20 + modificadores** como base universal.

- **Padrão:** Role 1d20, adicione os modificadores relevantes, compare ao DC (Difficulty Class).
- **Vantagem:** Role 2d20, use o maior. Concedida por posicionamento favorável, preparação, habilidade de classe ou narrativa.
- **Desvantagem:** Role 2d20, use o menor. Imposta por terreno adverso, condição negativa, ou ação arriscada sem preparo.
- **LUK:** O atributo LUK concede um dado adicional menor (d4) que pode ser somado a qualquer rolagem uma vez por turno. O jogador declara o uso antes de rolar o d4.

---

## 2. Escala de Resultado — 5 Graus

Toda ação com resultado variável é resolvida nesta escala:

| Resultado | Condição |
|-----------|----------|
| **Falha Crítica** | Natural 1 (sempre), ou margem ≤ −6 abaixo do DC |
| **Falha** | Margem de −1 a −5 abaixo do DC |
| **Neutro** | Exatamente no DC (empate — o GM decide quem ganha com base no contexto) |
| **Sucesso** | Margem de +1 a +5 acima do DC |
| **Sucesso Crítico** | Natural 20 (sempre), ou margem ≥ +6 acima do DC |

**Passe automático:** Se o total de modificadores e bônus fixos de um personagem já excede o DC sem rolar, a ação é bem-sucedida automaticamente — sem necessidade de rolagem. O GM narra o resultado como dado.

---

## 3. Estrutura do Ataque

### 3.1 Rolagem de Ataque

```
Rolagem de Ataque = d20 + Modificador de Atributo + Bônus de Proficiência + outros bônus
```

O total é comparado ao **DC de Defesa** do alvo.

- **DC de Defesa** = 10 + Modificador de DEX do alvo + Bônus de armadura + outros modificadores
- O alvo pode reagir ativamente (interpor escudo, esquivar) declarando uma **reação** — rola 1d20 + modificador relevante como contraposição.

### 3.2 Tipos de Ataque e Atributo Base

| Tipo de Ataque | Atributo de Ataque | Atributo de Dano |
|---|---|---|
| Físico — força bruta (espada, machado, arremesso pesado) | STR | STR |
| Físico — precisão (estoque, adaga, tiro de precisão) | DEX | DEX |
| Magia elemental (fogo, gelo, terra, ar, energia) | INT | INT |
| Magia espiritual / social / ilusão | CAR | CAR |
| Magia híbrida (elemental + espírito) | INT + CAR (média) | INT ou CAR — o maior |
| Ataque à distância físico (arco padrão) | DEX | DEX |

### 3.3 Dano

O dado de dano varia pela arma ou feitiço utilizado (definido na ficha do personagem ou na receita do feitiço). O modificador de atributo é somado ao resultado:

```
Dano = Dado da Arma/Feitiço + Modificador de Atributo
```

---

## 4. Iniciativa

No início de um combate, todos os participantes rolam iniciativa:

```
Iniciativa = d20 + Modificador de DEX + (d4 de LUK, opcional — declarar antes de rolar)
```

- Ordem de turno: do maior para o menor.
- **Empate:** o participante com DEX maior age primeiro. Se ainda empatado, rola d6 para desempatar.
- **Surprise round:** se um lado surpreende o outro, age primeiro com vantagem na primeira rodada. O lado surpreendido não pode usar reações nessa rodada.
- **Surpresa em combate já ativo** (ex: reforço inimigo chegando): o novo participante entra na ordem de iniciativa existente no slot correspondente ao seu roll.

---

## 5. Críticos e Falhas Críticas

### 5.1 Sucesso Crítico (Natural 20)

- O ataque sempre acerta, independente do DC de Defesa.
- Dano: role o dado de dano **duas vezes** + modificador de atributo + role o **dado de LUK** (d4) e some.
- O GM narra uma consequência narrativa favorável além do dano (inimigo derrubado, desarme, abertura de flanco, etc.).

### 5.2 Falha Crítica (Natural 1)

- O ataque sempre falha, independente dos modificadores.
- O GM determina a consequência com base na situação:
  - Arma escorrega / posição comprometida (exposição de flanco)
  - Magia desvia para aliado (se `friendly_fire: false`, afeta apenas narrativamente — susto, sem dano)
  - Ação consome turno e gera abertura para contra-ataque com vantagem
- A consequência deve ser proporcional ao contexto — falha crítica não é morte automática, é uma complicação séria.

---

## 6. Múltiplos Atacantes e Flanqueamento

- Cada atacante rola separadamente contra o mesmo alvo.
- **Flanqueamento:** dois atacantes em lados opostos do alvo concedem **vantagem** a ambos os ataques naquele turno.
- **Ataque coordenado:** se dois ou mais atacantes declaram ataque simultâneo ao mesmo alvo (dentro do batch de 3s), o GM resolve como flanqueamento automaticamente se a narrativa permitir.

---

## 7. Ataques de Área em Grupo Misto

Quando um feitiço ou ação afeta uma área com aliados e inimigos:

- `friendly_fire: false` — aliados não sofrem dano mecânico. Narrar como esquiva instintiva, barreira de sorte, ou desvio no último segundo.
- O GM deve narrar a tensão e o risco mesmo sem dano real ("a chama varreu a sala, Kael sentiu o calor na nuca mas saiu intacto").
- **Exceção:** aliado incapacitado (inconsciente, preso) dentro da zona de área — GM determina se a regra de friendly fire se aplica ou se o contexto narrativo exige dano.

---

## 8. Combate em Terreno Especial

| Terreno | Modificador |
|---------|-------------|
| Ruína instável (piso quebrado, debris) | −2 em ataques físicos; DC de movimento aumentado |
| Zona corrupta (T1-T2) | −1 em conjurações; +5 ao DC de backfire |
| Zona corrupta (T3-T4) | −2 em conjurações; +10 ao DC de backfire; vantagem para inimigos nativos |
| Zona corrupta (T5) | −4 em conjurações; backfire automático em spells Tier 5+; desvantagem em tudo |
| Água rasa (até o joelho) | −1 em ataques físicos de velocidade (DEX) |
| Água funda (acima da cintura) | −3 em todos os ataques físicos; conjurações de energia têm desvantagem |
| Altitude extrema / vento forte | −2 em ataques à distância; DC de arco aumentado em 4 |
| Escuridão total sem visão mágica | Desvantagem em todos os ataques; DC de Defesa efetivo +4 |
| Fragmento Aeridiano a ≤50m | Conjurações completamente estáveis — sem risco de backfire |

---

## 9. Fuga de Combate

Um personagem pode tentar fugir de combate por uma das três condições:

1. **Distância:** Se o personagem consegue se afastar mais do que o inimigo consegue percorrer em 3 turnos consecutivos (calculado com base na velocidade de movimento), a fuga é bem-sucedida.
2. **Ocultação:** Sair do campo de visão do inimigo E passar em **3 testes consecutivos de Furtividade** (DEX, DC determinado pelo nível do inimigo).
3. **Zona neutra:** Entrar em território ou local onde o inimigo não possa ou não queira seguir (templo, jurisdição diferente, zona de armistício).

**Ataque de oportunidade:** ao declarar fuga, o inimigo pode fazer um ataque de oportunidade com vantagem antes do personagem sair do alcance. Se o dano derruba o personagem a 0 HP, a fuga falha.

**Fuga de Boss:** requer as condições 1 ou 3. Bosses geralmente têm velocidade superior — condição 2 exige 5 testes bem-sucedidos em vez de 3.

---

## 10. Rendição de Inimigo

- Inimigo anuncia rendição quando HP ≤ 20% ou quando a narrativa determina que a luta está perdida.
- O GM rola uma verificação de moralidade/instinto do inimigo (DC 12 baseado em INT ou CON) — inimigos fanáticos ou de baixa INT não se rendem.
- **O que acontece:** o grupo pode aceitar (prisioneiro, informação, aliança temporária), recusar (inimigo foge ou luta até a morte), ou executar (consequência de reputação com testemunhas).
- Inimigo rendido que é poupado tem chance (DC 15 CAR do personagem) de fornecer informação útil ou criar gancho de missão.

---

## 11. Batalha Simultânea (Batch de 3s)

Quando dois jogadores declaram ações diferentes ao mesmo tempo:

1. O GM avalia qual ação estaria "mais avançada" na linha do tempo narrativa.
2. Essa ação é resolvida primeiro.
3. Se houve empate de progressão narrativa, desempata por **iniciativa** (quem tem maior iniciativa ativa age primeiro).
4. Em casos onde as ações são completamente paralelas e independentes (Jogador A em combate no andar de baixo, Jogador B negociando no andar de cima), o GM resolve as duas na mesma resposta, estruturada em blocos separados.

---

## 12. Combate Contra NPC Aliado (Traição / Controle Mental)

- NPC aliado controlado é tratado como inimigo para fins mecânicos.
- O GM não revela o DC de defesa do NPC aliado (para manter a tensão narrativa).
- Se o jogador declarar ataque não-letal: DC de Defesa normal, mas dano resulta em incapacitação em vez de morte.
- Matar um NPC aliado sob controle mental: sem penalidade de reputação, mas requer resolução narrativa (testemunhas, reação das facções).
- Matar um NPC aliado em traição confirmada: consequência de reputação padrão com a facção do NPC (veja [aerus_mechanics_systems.md]).

---

## 13. Boss Phase Change

**Gatilho:** HP abaixo de 30% OU evento narrativo predefinido pelo GM (chegada de reforço, item destruído, ritual completado).

- A phase change não é anunciada com antecedência.
- O boss age **imediatamente** ao cruzar o limiar — fora da ordem de iniciativa.
- A fase 2 pode incluir: restauração parcial de HP (até 50% do máximo), novas habilidades, modificadores de terreno, summons.
- O GM deve ter a narrativa da phase change preparada antecipadamente. O modelo de narração está em [aerus_gm_guide.md §Boss Phase Change].

---

## 14. PvP

PvP só ocorre em **arenas especiais** distribuídas pelo mundo (locais designados mecanicamente como zonas de duelo). Fora desses locais, ataques de um jogador contra outro são tratados narrativamente — o GM media o conflito sem resolução mecânica de dano permanente.

Dentro de uma arena: resolve-se com as mesmas regras de combate padrão, incluindo permadeath se `permadeath: true`.
