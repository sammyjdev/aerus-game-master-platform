# Material core para artigo de LinkedIn — "Eu treinei uma IA local por dias. Depois descobri que não precisava dela."

> Tudo que você precisa para escrever um artigo forte: o arco narrativo, os números,
> os achados contra-intuitivos, as falas-âncora e as lições. Use como matéria-prima.

---

## A tese (o gancho)

**Passei uma maratona treinando um Small Language Model local para ser o narrador de um
RPG. No fim, um modelo de nuvem barato + os meus próprios exemplos como RAG + 50 linhas
de validação entregaram mais qualidade, por menos custo e esforço. O trabalho não foi
perdido — virou outra coisa.**

É uma história de **build vs buy** decidida por **evidência** (benchmarks e um teste cego),
não por opinião — e cheia de reviravoltas que contrariam a intuição.

---

## O arco (estrutura sugerida do artigo)

1. **A premissa romântica:** "IA local, custo zero, modelo só meu." Treinar um SLM (Mistral
   7B→12B) na minha RTX 4070 Ti para narrar meu RPG.
2. **O primeiro soco:** o modelo treinado **regurgitava as próprias regras** em vez de narrar.
   Um bug de uma linha (`completion_only_loss=False`) — a loss estava treinando o modelo a
   *repetir o prompt*.
3. **A obsessão por dados:** automatizei a geração de um dataset "perfeito" com 17 agentes em
   paralelo (98,9% de aproveitamento). 794 exemplos curados. O modelo melhorou — e travou
   num teto de ~67%.
4. **A reviravolta nº1 — a métrica mentia:** comparei modelos de nuvem no MESMO teste. O
   melhor da métrica foi o **pior** no julgamento humano. A métrica media *obediência de
   formato*, não *qualidade*.
5. **A reviravolta nº2 — o juiz cego:** fiz um teste A/B onde eu não sabia qual modelo era
   qual. O meu SLM local perdeu para modelos de nuvem que eu nem tinha treinado. Mas ganhou
   UMA cena (a de morte) — e isso ensinou algo.
6. **A virada de chave:** e se eu desse os meus exemplos curados para o modelo de nuvem como
   **RAG**, em vez de treinar com eles? O frontier entende "quando ser conciso vs prolixo"
   na hora. Os 794 exemplos viram o **banco de RAG**, não dado de treino.
7. **O detalhe que ninguém vê:** a narração saía em 3ª pessoa fria ("O Callum sofre..."). O
   correto, imersivo, é 2ª pessoa ("Você, Callum, sofre..."). Uma linha de prompt resolveu —
   no modelo de nuvem. No SLM, exigiria retreino.
8. **A garantia:** como confiar numa IA generativa? Um **guardrail determinístico** que valida
   cada saída contra as regras checáveis e regenera/corrige as que falham.
9. **A lição:** o valor não estava no modelo. Estava em **saber o que é qualidade** e em ter
   **um jeito de medir e garantir**.

---

## Os números (use à vontade — todos reais e medidos)

**Progressão do SLM local (Density gate):**
- 7B original: ~0% (quebrado, regurgitava regras)
- 7B gate-curado: 42%
- Nemo 12B (794 exemplos): **67-68%** (teto prático)

**O benchmark de nuvem no MESMO gate (com prompt de caps):**
- Claude 3.5 Haiku: **82,5%**
- DeepSeek V3: 75,4%
- Gemini 2.5 Flash: 70,2%
- Meu SLM (Nemo): 67%
- Claude Haiku 4.5: **29,8%**

**O teste cego (eu como juiz, sem saber qual era qual):**
- Haiku 4.5 (o **pior** da métrica, 29,8%) **venceu 4 de 6 cenas**.
- Haiku 3.5 (o **melhor** da métrica, 82,5%) ficou em **último**.
- Meu SLM local venceu **1 cena** (a de morte) — de graça, offline.
- Rodada 2: **DeepSeek V3.2 empatou com o Haiku 4.5** — por **~1/4 do custo**.

**Custo final (com caching):**
- DeepSeek: **~$0,13 / 1000 turnos**
- Haiku: ~$1,00 / 1000 turnos
- (O output domina o custo — e o do Haiku é 12× o do DeepSeek.)

**Infra (a parte chata e real):**
- 12B = teto para treinar E servir em 12GB de VRAM.
- 14B → vira I/O-bound (offload VRAM↔RAM pelo PCIe): ~4h de treino vs ~30min do 12B.
- Gemma 3 12B nem carregou (multimodal não cabe). Qwen deu NaN (tokenizer PT inflava o
  prompt e truncava a resposta). Cada base é uma armadilha diferente.

---

## Os achados contra-intuitivos (o ouro do artigo)

1. **"Benchmark não é qualidade."** O campeão do meu teste automático foi o pior no
   julgamento humano. Métricas rígidas medem o que é fácil medir (contar frases), não o que
   importa (a narração é boa de ler?). Um modelo melhor escreve prosa mais rica — e "falha"
   na métrica de concisão.

2. **"O modelo mais novo pontuou pior."** Haiku 4.5 (mais novo) perdeu para Haiku 3.5 na
   métrica — porque é tunado para ser mais elaborado, e a métrica punia comprimento. Mas
   ganhou no julgamento humano. *Capacidade ≠ obediência cega a uma régua.*

3. **"O dataset que eu curei tinha um viés contra a própria bíblia."** 70% dos meus exemplos
   usavam 3ª pessoa fria, contradizendo a regra de 2ª pessoa. Eu estava ensinando o modelo a
   errar. (No nuvem: 1 linha conserta. No SLM: retreino.)

4. **"Fine-tuning vs RAG não é build vs buy — é onde você coloca o conhecimento."** Treinar
   assa o conhecimento no peso (caro de mudar). RAG injeta na hora (barato de mudar). Para
   VOZ e ESTILO, RAG ganhou.

5. **"No RPG, o narrador não pode falar antes do dado."** O melhor modelo "vazou" o resultado
   de uma perícia antes da rolagem. Isso não é problema de prosa — é de **arquitetura de
   jogo**: resolver/pedir o dado primeiro, narrar a consequência depois.

---

## Falas-âncora (frases prontas pra citar)

- *"Eu não estava construindo um modelo. Estava descobrindo o que era qualidade — e como
  medir e garantir isso."*
- *"O melhor da métrica foi o pior no teste cego. Aprendi a desconfiar do meu próprio
  benchmark."*
- *"Os 794 exemplos que eu curei para treinar não foram desperdiçados. Viraram o RAG e o
  espec de voz. O trabalho mudou de lugar, não de valor."*
- *"Prompt inclina. Guardrail garante. As duas coisas são necessárias."*
- *"A pergunta certa não era 'qual modelo treinar', era 'qual a forma mais barata de
  garantir a voz que eu quero'."*

---

## As lições técnicas (credibilidade)

- **`completion_only_loss`**: se a loss treina sobre o prompt, o modelo aprende a repetir o
  prompt. Mascarar a loss na resposta é o feijão-com-arroz que ninguém conta.
- **Dataset eval-curado**: treinar só com exemplos que passam no seu próprio critério de
  aceitação é uma forma barata e poderosa de alinhar comportamento.
- **Tokenizers diferentes quebram tamanhos fixos**: o mesmo texto vira 600 tokens no Mistral
  e 860 no Qwen. `max_seq_length` fixo → resposta truncada → NaN.
- **Guardrail de runtime**: auto-fix grátis (regex) para o mecânico, regeneração só para o
  substantivo, fallback no fim. ~99% de conformidade nas regras checáveis.
- **Caching**: badrata o input estático, não o output. Em narração, o output domina — por
  isso o modelo de output barato (DeepSeek) ganha mesmo com cache nos dois.

---

## O que NÃO romantizar (honestidade = autoridade)

- O SLM local **tem nicho**: ganhou a cena de morte, é $0/offline. Não é lixo — é fallback.
- O guardrail tem **custo real** (~1,6 chamadas/turno) e **buracos** (regex de verbo frágil
  deu falso-positivo). Mostre isso — honestidade técnica vale mais que hype.
- O subjetivo (voz, tom) **não é 100% garantível por código**. Prompt+RAG inclinam;
  amostragem monitora. Admita os limites.

---

## CTA sugerido para o post

> "Stack: Mistral/Unsloth, llama.cpp, ChromaDB, DeepSeek/Claude via API, e um gate honesto
> que me obrigou a confiar mais no meu julgamento que no meu benchmark. Repo e documento de
> decisão nos comentários. Qual foi a última vez que um benchmark te enganou?"

---

## Hashtags / ângulos

`#LLM #RAG #FineTuning #AIEngineering #BuildVsBuy #PromptEngineering #GameDev #MLOps`

Ângulos alternativos de manchete:
- "RAG venceu fine-tuning no meu projeto — e os dados explicam por quê."
- "Por que parei de confiar em benchmarks de LLM (com números)."
- "O modelo de IA mais novo pontuou pior. A história por trás disso."
