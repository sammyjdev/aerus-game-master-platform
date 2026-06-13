"""hosted_narrator.py - Hosted frontier narrator (DeepSeek/Haiku) with RAG + guardrail.

Why this exists: a controlled investigation (see aerum-narrator/DECISAO_NARRADOR.md)
showed that a cheap hosted model + the curated 794 examples as RAG + a deterministic
guardrail beats a locally fine-tuned SLM on human-judged quality, at a fraction of the
cost/effort. This module is that narrator.

Pipeline per turn:
    4-layer prompt (kernel + soft cap + 2nd-person + no-em-dash/impact + RAG few-shot)
      -> model (non-streamed, so we can validate before showing)
      -> AUTO-FIX  (strip em-dash; free)
      -> VALIDATE  (machine-checkable bible rules)
      -> pass: return | fail: regenerate with correction (up to N) | else: best effort
"""
from __future__ import annotations

import logging
import re

from openai import AsyncOpenAI

from .infrastructure.config.config_loader import load_narration_bible_kernel

logger = logging.getLogger(__name__)

GLOBAL_MAX_SENTENCES = 6  # soft sanity ceiling; per-scene length comes from RAG examples

# Kept in sync with aerum-narrator/eval/cliche_detection.py + the narration bible.
_FORBIDDEN = [
    "você sente", "você percebe", "você nota", "sua mente", "seu coração",
    "no fundo do seu ser", "algo dentro de você", "você treme", "você hesita",
    "parece que", "acariciando", "burburinho", "microcosmo", "ferida sangrante",
    "introspectivamente", "aos poucos", "instintivamente", "por um momento",
    "mistura única", "epifania", "envolvendo você", "de repente", "com um sorriso",
    "como se fosse", "o peso da situação", "a tensão é palpável", "o ar está pesado",
    "uma sensação estranha", "você fica atordoado", "você está envenenado",
    "você levou crítico", "você subiu de nível", "você ganhou xp", "em essência",
    "o que realmente importa", "é importante notar", "vale ressaltar",
]

_STYLE_RULES = (
    "REGRAS DE ESTILO (obrigatórias):\n"
    "- 2ª PESSOA quando o foco é o jogador: 'Você, {nome}, ...' / '{nome}, você ...'. "
    "Nunca 3ª pessoa distante ('O {nome}...'). Descrição de objeto/mundo pode ser impessoal.\n"
    "- SEM TRAVESSÃO (—): nunca use travessão longo. Pausa e impacto vêm de frases CURTAS e SECAS.\n"
    "- IMPACTO: ritmo de batida; ênfase pela palavra e pelo corte seco, não por pontuação artificial.\n"
    "- Narre APENAS o que o personagem percebe agora. Sem metadado, sem JSON."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _count_sentences(text: str) -> int:
    return len([s for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()])


def _detect_cliches(text: str) -> list[str]:
    low = text.lower()
    return [p for p in _FORBIDDEN if p in low]


def auto_fix(text: str) -> str:
    """Free deterministic fixes (no model call): em-dash -> dry pause."""
    t = re.sub(r"\s*—\s*", ". ", text)
    t = re.sub(r"\.\s*\.", ".", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def validate(text: str, player_names: list[str]) -> list[str]:
    """Return machine-checkable bible violations (empty = compliant)."""
    issues: list[str] = []
    if not text:
        return ["narração vazia"]
    if _count_sentences(text) > GLOBAL_MAX_SENTENCES:
        issues.append(f"verbosidade excessiva (> {GLOBAL_MAX_SENTENCES} frases)")
    cliches = _detect_cliches(text)
    if cliches:
        issues.append(f"clichês: {cliches}")
    if "—" in text:
        issues.append("travessão presente")
    # 2nd-person heuristic: a player name as 3rd-person subject without any "você"
    if not re.search(r"\bvoc[êe]\b", text, re.I):
        for name in player_names:
            if re.search(rf"\b{name}\b", text):
                issues.append("3ª pessoa (use 2ª pessoa: 'Você, {})')".format(name))
                break
    return issues


def build_messages(
    user_message: str,
    rag_examples: list[dict[str, str]],
    location: str,
    tension: int,
    language: str,
    player_name: str,
    correction: str | None = None,
) -> list[dict[str, str]]:
    """4-layer prompt: kernel + soft cap + 2nd-person/no-dash + RAG few-shot + turn."""
    kernel = load_narration_bible_kernel()
    lang = "português do Brasil" if language == "pt" else "inglês"
    system = (
        f"{kernel}\n\nVocê é o Game Master do RPG Aerum. Narre em {lang}.\n"
        f"Siga o ESTILO e o COMPRIMENTO dos exemplos abaixo. "
        f"Local: {location}. Tensão: {tension}/10. Jogador em foco: {player_name}.\n"
        f"{_STYLE_RULES}\nGere APENAS a narração."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for ex in rag_examples:
        messages.append({"role": "user", "content": ex["input"]})
        messages.append({"role": "assistant", "content": auto_fix(ex["narration"])})
    user = user_message
    if correction:
        user = f"{user_message}\n\n[Correção: sua resposta anterior violou: {correction}. Refaça corrigindo, mantendo a voz.]"
    messages.append({"role": "user", "content": user})
    return messages


async def narrate(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    rag_examples: list[dict[str, str]],
    location: str,
    tension: int,
    language: str,
    player_name: str,
    player_names: list[str],
    max_attempts: int = 3,
    max_tokens: int = 320,
) -> dict:
    """Generate a bible-compliant narration. Returns {text, calls, status}."""
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    correction: str | None = None
    last = ""
    calls = 0
    for _ in range(max_attempts):
        messages = build_messages(
            user_message, rag_examples, location, tension, language, player_name, correction
        )
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens, temperature=0.75,
        )
        calls += 1
        raw = (resp.choices[0].message.content or "").strip()
        fixed = auto_fix(raw)
        issues = validate(fixed, player_names)
        last = fixed
        if not issues:
            logger.info("hosted_narrator: compliant in %d call(s)", calls)
            return {"text": fixed, "calls": calls, "status": "pass"}
        correction = "; ".join(issues)
    logger.warning("hosted_narrator: returning best effort after %d calls; residual=%s",
                   calls, validate(last, player_names))
    return {"text": last, "calls": calls, "status": "best_effort"}
