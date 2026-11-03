# Engenharia de Sistemas de IA/ML & Otimização de Inferência: Guia de Experiência Prática

> **Documento de Referência Técnica & Posicionamento de Carreira em IA/ML**  
> **Caso de Estudo:** Plataforma Aerus Game Master (ExLlamaV3, Quantização EXL3, RAG Bank e Streaming Reativo).

---

## 1. Visão Geral e Contexto de Mercado

O mercado de Engenharia de IA amadureceu e se dividiu em dois grandes grupos:
1. **Consumidores de API (Nível Superficial):** Desenvolvedores que chamam endpoints comerciais (`/chat/completions`) com frameworks genéricos e enfrentam problemas crônicos de custo, latência e dependência de terceiros.
2. **Engenheiros de Sistemas de IA / LLM Systems Engineers (Nível Profundo):** Profissionais que entendem restrições de hardware, alocação de memória na GPU (VRAM), técnicas avançadas de quantização, calibração de modelos, compressão de KV-cache, streaming token-a-token e tradeoffs empíricos de qualidade (*Build vs Buy*).

Este documento formaliza as decisões de arquitetura, métricas de engenharia e estudos de caso práticos desenvolvidos na plataforma **Aerus RPG**, estruturando-os como material de portfólio, currículo e preparação para entrevistas técnicas seniores.

---

## 2. As 4 Grandes Narrativas de Engenharia Comprovadas

```
+------------------------------------------------------------------------------------------------+
|                                AERUS AI SYSTEMS ARCHITECTURE                                   |
+------------------------------------------------------------------------------------------------+
|                                                                                                |
|   [ Cliente React SPA ] <--- (WebSocket Streaming: Delta Tokens) ---> [ Backend FastAPI ]      |
|                                                                               |                |
|           +-------------------------------------------------------------------+                |
|           |                                                                                    |
|           v                                                                                    |
|   +---------------------------------------+   +--------------------------------------------+   |
|   | 1. High-Speed Local GPU Inference     |   | 2. Hybrid Fallback & Gateway               |   |
|   |    - ExLlamaV3 + TabbyAPI             |   |    - Ollama (qwen2.5:14b)                  |   |
|   |    - UnslopNemo 12.2B EXL3 (4.25 bpw) |   |    - OpenRouter (BYOK / Frontier Models)   |   |
|   |    - Head FP16 (Unquantized)          |   |    - Fernet Encrypted Keys at Rest         |   |
|   |    - Q8 Quantized KV-Cache (16k Ctx)  |   +--------------------------------------------+   |
|   |    - Speed: 57.4 tps | Latency: 17.6ms|                                                    |
|   +---------------------------------------+                                                    |
|           |                                                                                    |
|           v                                                                                    |
|   +----------------------------------------------------------------------------------------+   |
|   | 3. RAG Bank & State Persistence Layer                                                  |   |
|   |    - ChromaDB (Lore, Bestiário & 794 exemplos curados de voz narrativa)                |   |
|   |    - SQLite WAL com isolamento por Campanha e Travas Concorrentes (asyncio.Lock)       |   |
|   +----------------------------------------------------------------------------------------+   |
|                                                                                                |
+------------------------------------------------------------------------------------------------+
```

---

### Narrativa 1: Otimização Extrema de Inferência Local na GPU (ExLlamaV3)

#### Desafio Técnico
Executar localmente um modelo de ponta de **12.2 Bilhões de parâmetros (Mistral Nemo / UnslopNemo v4.1)** com **16.384 tokens de contexto** dentro do limite estrito de **12 GB de VRAM** de uma GPU comercial (NVIDIA GeForce RTX 4070 Ti), sem causar falhas de falta de memória (*CUDA Out of Memory - OOM*) e mantendo tempo de resposta imperceptível para o usuário final.

#### Soluções e Técnicas Aplicadas
- **Quantização Personalizada EXL3 (`4.25 bpw`):** As 40 camadas Transformer foram quantizadas com pesos variáveis em precisão sub-byte via matriz Hessiana.
- **Isolamento de Head em FP16 (`-hb 16`):** Durante o processo de calibração padrão em 6-bit, a matriz de saída do vocabulário (131.072 tokens) gerava um pico transitório de alocação de ~2.5 GB, causando OOM. A fixação do `lm_head` em 16-bit unquantized eliminou esse overhead de calibração e preservou 100% da fidelidade semântica e do vocabulário em português.
- **Quantização de KV-Cache em `Q8`:** O cache de chaves/valores de atenção foi comprimido em 8-bit, liberando 50% de VRAM no contexto estendido sem degradação perceptível.

#### Métricas de Impacto Medidas
- **Velocidade de Geração:** **`57.36 tokens/segundo`** (~2.5x a 3x mais rápido que implementações GGUF/llama.cpp equivalentes).
- **Latência Inter-Token:** **`17.61 ms / token`** (emissão fluida e contínua).
- **Time-to-First-Token (TTFT):** **`67.8 ms`** com prefix cache / warm prompt.
- **Consumo de VRAM:** **`9.8 GB`** estável, deixando **`>2.2 GB de folga`** para o sistema operacional e buffers de renderização gráfica.

---

### Narrativa 2: Decisão Empírica "Build vs Buy" & RAG Adaptativo

#### Desafio Técnico
Determinar se a criação de um modelo especialista proprietário (Fine-Tuning de SLM local Mistral 7B/12B) superava a utilização de modelos de fronteira acessíveis combinados com Retrieval-Augmented Generation (RAG).

#### Metodologia e Descobertas
1. **Curadoria do Dataset:** Construção manual e validação de um corpus de **794 pares de alta densidade** de ações e respostas narrativas no tom *grimdark*.
2. **Treinamento e Ajuste:** Execução de fine-tuning com correção de `completion_only_loss` para evitar perda de gradiente em prompts.
3. **Avaliação Cega (Human A/B Testing):** Modelos locais fine-tunados atingiram um platô de ~65% de conformidade de tom, perdendo sistematicamente em testes cegos para modelos de fronteira baratos (DeepSeek / Claude Haiku).
4. **Pivot Arquitetural:** O dataset de 794 exemplos foi convertido em um **RAG Bank** indexado no ChromaDB. A narrativa passou a ser condicionada por *few-shot context injection* dinâmico somado a um guardrail determinístico (~50 linhas) no backend.

#### Lição de Engenharia
> *"O valor de negócio não reside no peso bruto do modelo, mas na definição quantificável do que constitui uma resposta de alta qualidade e nos dados de domínio protegidos."*

---

### Narrativa 3: Streaming de Alta Concorrência & Orquestração Reativa

#### Desafio Técnico
Manter múltiplos jogadores interagindo simultaneamente em uma campanha sem que as respostas do Game Master fiquem dessincronizadas, sem travar o event loop do FastAPI e sem fazer o usuário esperar o fim da geração para ler o texto.

#### Soluções Aplicadas
- **Streaming Token-a-Token via WebSocket:** Resposta gerada via iterador assíncrono conectado ao TabbyAPI (`stream=True`), despachando deltas instantaneamente para o cliente React.
- **Action Batching com Janela Temporal:** Implementação de janela de agregação de 3 segundos para fundir intenções de combate/viagem de múltiplos jogadores em um único prompt consolidado.
- **Travas Concorrentes Observáveis (`asyncio.Lock`):** Garantia de atomicidade nas transações do SQLite WAL, impedindo condições de corrida durante atualizações simultâneas de inventário, status e mutações de classe.

---

### Narrativa 4: Gestão de Custos, Roteamento Híbrido & BYOK com Criptografia

#### Desafio Técnico
Oferecer suporte flexível a diferentes ambientes operacionais (jogadores com GPU própria, servidores dedicados ou usuários finais sem GPU).

#### Soluções Aplicadas
- **Roteamento Dinâmico em 3 Níveis:**
  1. *Nível 1 (Local GPU):* ExLlamaV3 via TabbyAPI para custo marginal zero e latência mínima.
  2. *Nível 2 (Local CPU/Fallback):* Ollama com modelos auxiliares (`qwen2.5:14b`, `phi4:mini`) para extração estruturada de JSON e compressão de memória.
  3. *Nível 3 (Hosted Gateway):* OpenRouter com suporte a BYOK (*Bring Your Own Key*).
- **Segurança de Chaves BYOK:** Criptografia simétrica com **Fernet** para chaves de API armazenadas em repouso no banco de dados.

---

## 3. Bullets Prontos para Currículo e LinkedIn

### Como descrever esta experiência no Currículo (Exemplos)

#### Opção A — Foco em LLM Systems & Inference Optimization
```markdown
* Projetou e implementou pipeline de inferência local de baixa latência utilizando ExLlamaV3 e TabbyAPI para modelos de 12.2B parâmetros (Mistral Nemo), atingindo throughput de 57.4 tokens/s e latência inter-token de 17.6 ms em GPU de 12GB.
* Otimizou o footprint de memória na GPU aplicando quantização híbrida EXL3 (4.25 bpw), preservação de vocabulário FP16 unquantized e compressão de KV-Cache em Q8, suportando 16k tokens de contexto em apenas 9.8 GB de VRAM.
* Implementou arquitetura de streaming reativa via WebSocket assíncrono (FastAPI/React) com batching dinâmico de turnos e persistência concorrente em SQLite WAL.
```

#### Opção B — Foco em AI Ops, RAG & Arquitetura Híbrida
```markdown
* Liderou estudo empírico "Build vs Buy" comparando fine-tuning de SLMs proprietários com RAG semântico sobre 794 exemplos curados, reduzindo custos de inferência e elevando a aderência estilística com guardrails determinísticos.
* Desenvolveu gateway multi-provedor com fallback automático (GPU Local -> Ollama -> OpenRouter) e criptografia simétrica Fernet para chaves BYOK de usuários.
* Estabeleceu harness de testes automatizados com mais de 450 testes unitários e de integração (pytest, vitest, e2e), garantindo zero regressões mecânicas e 100% de isolamento entre campanhas.
```

---

## 4. Guia de Preparação para Entrevistas Técnicas

### Pergunta 1: *"Como você lida com restrições de VRAM ao rodar modelos grandes localmente?"*
**Resposta Estruturada:**
> *"Em vez de recorrer apenas a formatos genéricos como GGUF/llama.cpp, analiso o perfil de alocação por camada. No projeto Aerus, quantizamos um modelo de 12.2B em EXL3 (4.25 bpw) na RTX 4070 Ti de 12GB. O ponto crítico foi identificar que calibrar o `lm_head` em 6-bit causava um spike de alocação transitório de 2.5 GB. Mantivemos o `lm_head` em FP16 (16-bit unquantized), o que zerou o overhead de calibração, manteve a precisão do vocabulário e, aliado ao KV-cache em Q8, permitiu rodar 16k tokens de contexto consumindo apenas 9.8 GB de VRAM com mais de 57 tokens/s."*

---

### Pergunta 2: *"Quando vale a pena fazer Fine-Tuning versus usar RAG?"*
**Resposta Estruturada:**
> *"Fine-tuning é ideal para ensinar formato rígido, sintaxe ou novas linguagens, mas muitas vezes perde para RAG em transferência de estilo e factualidade. No nosso caso, curamos 794 exemplos de tom narrativo e testamos fine-tuning em Mistral 7B/12B. Em avaliações cegas humanas A/B, o fine-tune local atingiu um platô qualitativo. Convertemos os dados em um RAG Bank no ChromaDB com injeção contextual em modelos de fronteira, alcançando qualidade superior, menor custo total de propriedade e facilidade de atualização sem necessidade de re-treinamento."*

---

### Pergunta 3: *"Como você garante baixa latência no streaming de IA para a interface?"*
**Resposta Estruturada:**
> *"Trabalho em três frentes: ingestão de prompt (Time to First Token), velocidade de geração (Tokens/s) e transporte. Para o TTFT, utilizamos prefix caching na GPU, baixando o tempo de primeiro token para menos de 70 ms em requisições subsequentes. Na geração, a quantização EXL3 garante latência inter-token de ~17.6 ms. No transporte, usamos WebSocket assíncrono com broadcast de deltas em tempo real, evitando o overhead de polling ou conexões HTTP repetidas."*

---

## 5. Roadmap de Evolução Técnica Contínua

| Área | Próximo Passo de Exploração | Impacto Técnico |
|---|---|---|
| **Speculative Decoding** | Adicionar um modelo rascunho de 1B/2B no TabbyAPI para predizer tokens do 12B | Elevar geração de ~57 tps para **80–110+ tps** |
| **LoRA Hot-Swapping** | Carregamento dinâmico de adapters LoRA por facção/NPC em tempo de execução | Especialização temática instantânea sem duplicar o modelo base |
| **Avaliação Contínua (LLM Evals)** | Implementar pipeline de testes com framework Ragas / DeepEval | Métricas automatizadas de alucinação e fidelidade às regras a cada commit |
