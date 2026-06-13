# Core material for a LinkedIn article — "I spent days training a local AI. Then I found out I didn't need it."

> Everything you need to write a strong article: the narrative arc, the numbers,
> the counter-intuitive findings, the anchor quotes, and the lessons. Use it as raw material.

---

## The thesis (the hook)

**I spent a marathon training a local Small Language Model to be the narrator of an
RPG. In the end, a cheap cloud model + my own examples as RAG + 50 lines of validation
delivered more quality, for less cost and effort. The work wasn't wasted — it just
became something else.**

It's a **build vs buy** story decided by **evidence** (benchmarks and a blind test),
not opinion — and full of twists that defy intuition.

---

## The arc (suggested article structure)

1. **The romantic premise:** "Local AI, zero cost, a model that's all mine." Training an SLM
   (Mistral 7B→12B) on my RTX 4070 Ti to narrate my RPG.
2. **The first punch:** the trained model **regurgitated its own rules** instead of narrating.
   A one-line bug (`completion_only_loss=False`) — the loss was training the model to
   *repeat the prompt*.
3. **The obsession with data:** I automated the generation of a "perfect" dataset with 17 agents in
   parallel (98.9% yield). 794 curated examples. The model improved — and stalled
   at a ceiling of ~67%.
4. **Twist #1 — the metric was lying:** I compared cloud models on the SAME test. The
   best one on the metric was the **worst** in human judgment. The metric measured *format
   obedience*, not *quality*.
5. **Twist #2 — the blind judge:** I ran an A/B test where I didn't know which model was
   which. My local SLM lost to cloud models I hadn't even trained. But it won
   ONE scene (the death one) — and that taught me something.
6. **The pivot:** what if I gave my curated examples to the cloud model as
   **RAG**, instead of training with them? The frontier model understands "when to be concise vs verbose"
   on the fly. The 794 examples become the **RAG bank**, not training data.
7. **The detail no one sees:** the narration came out in cold 3rd person ("Callum suffers...").
   The correct, immersive way is 2nd person ("You, Callum, suffer..."). One line of prompt fixed it —
   on the cloud model. On the SLM, it would require retraining.
8. **The guarantee:** how do you trust a generative AI? A **deterministic guardrail** that validates
   every output against the checkable rules and regenerates/corrects the ones that fail.
9. **The lesson:** the value wasn't in the model. It was in **knowing what quality is** and in having
   **a way to measure and guarantee it**.

---

## The numbers (use freely — all real and measured)

**Local SLM progression (Density gate):**
- 7B original: ~0% (broken, regurgitated rules)
- 7B gate-curated: 42%
- Nemo 12B (794 examples): **67-68%** (practical ceiling)

**The cloud benchmark on the SAME gate (with a caps prompt):**
- Claude 3.5 Haiku: **82.5%**
- DeepSeek V3: 75.4%
- Gemini 2.5 Flash: 70.2%
- My SLM (Nemo): 67%
- Claude Haiku 4.5: **29.8%**

**The blind test (me as judge, not knowing which was which):**
- Haiku 4.5 (the **worst** on the metric, 29.8%) **won 4 of 6 scenes**.
- Haiku 3.5 (the **best** on the metric, 82.5%) came in **last**.
- My local SLM won **1 scene** (the death one) — for free, offline.
- Round 2: **DeepSeek V3.2 tied with Haiku 4.5** — for **~1/4 of the cost**.

**Final cost (with caching):**
- DeepSeek: **~$0.13 / 1000 turns**
- Haiku: ~$1.00 / 1000 turns
- (Output dominates the cost — and Haiku's is 12× DeepSeek's.)

**Infra (the boring, real part):**
- 12B = ceiling for training AND serving on 12GB of VRAM.
- 14B → becomes I/O-bound (VRAM↔RAM offload over PCIe): ~4h of training vs ~30min for the 12B.
- Gemma 3 12B didn't even load (multimodal won't fit). Qwen returned NaN (the PT tokenizer inflated the
  prompt and truncated the response). Every base model is a different trap.

---

## The counter-intuitive findings (the gold of the article)

1. **"Benchmark is not quality."** The champion of my automated test was the worst in human
   judgment. Rigid metrics measure what's easy to measure (counting sentences), not what
   matters (is the narration good to read?). A better model writes richer prose — and "fails"
   the conciseness metric.

2. **"The newer model scored worse."** Haiku 4.5 (newer) lost to Haiku 3.5 on the
   metric — because it's tuned to be more elaborate, and the metric punished length. But
   it won in human judgment. *Capability ≠ blind obedience to a ruler.*

3. **"The dataset I curated had a bias against my own bible."** 70% of my examples
   used cold 3rd person, contradicting the 2nd-person rule. I was teaching the model to
   get it wrong. (On the cloud: 1 line fixes it. On the SLM: retraining.)

4. **"Fine-tuning vs RAG isn't build vs buy — it's where you put the knowledge."** Training
   bakes the knowledge into the weights (expensive to change). RAG injects it on the fly (cheap to change). For
   VOICE and STYLE, RAG won.

5. **"In an RPG, the narrator can't speak before the dice."** The best model "leaked" the result
   of a skill check before the roll. That's not a prose problem — it's a **game architecture**
   problem: resolve/request the roll first, narrate the consequence after.

---

## Anchor quotes (ready-to-cite lines)

- *"I wasn't building a model. I was discovering what quality was — and how to
  measure and guarantee it."*
- *"The best on the metric was the worst in the blind test. I learned to distrust my own
  benchmark."*
- *"The 794 examples I curated to train weren't wasted. They became the RAG and the
  voice spec. The work changed place, not value."*
- *"Prompt nudges. Guardrail guarantees. You need both."*
- *"The right question wasn't 'which model to train,' it was 'what's the cheapest way to
  guarantee the voice I want.'"*

---

## The technical lessons (credibility)

- **`completion_only_loss`**: if the loss trains over the prompt, the model learns to repeat the
  prompt. Masking the loss on the response is the bread-and-butter that no one talks about.
- **Eval-curated dataset**: training only on examples that pass your own acceptance
  criterion is a cheap and powerful way to align behavior.
- **Different tokenizers break fixed lengths**: the same text becomes 600 tokens in Mistral
  and 860 in Qwen. Fixed `max_seq_length` → truncated response → NaN.
- **Runtime guardrail**: free auto-fix (regex) for the mechanical, regeneration only for the
  substantive, fallback at the end. ~99% conformance on the checkable rules.
- **Caching**: it cheapens the static input, not the output. In narration, output dominates — that's
  why the cheap-output model (DeepSeek) wins even with caching on both.

---

## What NOT to romanticize (honesty = authority)

- The local SLM **has a niche**: it won the death scene, it's $0/offline. It's not garbage — it's a fallback.
- The guardrail has a **real cost** (~1.6 calls/turn) and **holes** (a fragile verb regex
  produced a false positive). Show that — technical honesty is worth more than hype.
- The subjective (voice, tone) **isn't 100% guaranteeable by code**. Prompt+RAG nudge;
  sampling monitors. Admit the limits.

---

## Suggested CTA for the post

> "Stack: Mistral/Unsloth, llama.cpp, ChromaDB, DeepSeek/Claude via API, and an honest
> gate that forced me to trust my own judgment more than my benchmark. Repo and decision
> document in the comments. When was the last time a benchmark fooled you?"

---

## Hashtags / angles

`#LLM #RAG #FineTuning #AIEngineering #BuildVsBuy #PromptEngineering #GameDev #MLOps`

Alternative headline angles:
- "RAG beat fine-tuning in my project — and the data explains why."
- "Why I stopped trusting LLM benchmarks (with numbers)."
- "The newer AI model scored worse. The story behind it."
