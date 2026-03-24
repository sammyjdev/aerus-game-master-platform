from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass

import httpx

OLLAMA_URL = "http://localhost:11434"
MODELS = ["qwen2.5:14b-instruct", "phi4:14b"]
RUNS_PER_CASE = 2
TIMEOUT_SECONDS = 300


@dataclass
class Case:
    name: str
    system: str
    user: str
    max_tokens: int
    expects_json: bool = False


CASES = [
    Case(
        name="summarizer_memory",
        system=(
            "VocÃª Ã© um sumarizador de RPG. Resuma fatos permanentes e consequÃªncias "
            "em atÃ© 6 linhas curtas em pt-BR. NÃ£o invente fatos."
        ),
        user=(
            "Turnos:\n"
            "Jogadores: Kael ataca o capitÃ£o cultista e toma 18 de dano.\n"
            "GM: O capitÃ£o recua, derruba um amuleto e foge para a cripta.\n"
            "Jogadores: Lyra usa magia de fogo para selar a porta da cripta.\n"
            "GM: A porta sela, mas a cidade entra em pÃ¢nico e o fogo se espalha para o mercado.\n"
            "Resuma focando em consequÃªncias permanentes e ganchos."
        ),
        max_tokens=220,
    ),
    Case(
        name="state_json_strict",
        system=(
            "VocÃª Ã© um parser de estado. Responda APENAS JSON vÃ¡lido sem markdown. "
            "Campos obrigatÃ³rios: tension_level (int), state_delta (obj), game_events (array)."
        ),
        user=(
            "Cena: Kael recebeu 12 de dano, ganhou 40 xp, Lyra ganhou item 'Runa Cinzenta'. "
            "A tensÃ£o subiu para 8 por causa da chegada do boss."
        ),
        max_tokens=220,
        expects_json=True,
    ),
    Case(
        name="secret_objective_hint",
        system=(
            "VocÃª Ã© GM tÃ¡tico. Gere um hint curto e indireto sobre objetivo secreto de facÃ§Ã£o, "
            "sem revelar explicitamente o objetivo."
        ),
        user=(
            "FacÃ§Ã£o: guild_of_threads. Objetivo secreto: recuperar o artefato sem a Igreja perceber. "
            "Progresso atual: 60%. Gere 1 hint narrativo em atÃ© 2 frases."
        ),
        max_tokens=120,
    ),
]


def call_ollama(model: str, system: str, user: str, max_tokens: int) -> tuple[str, float, dict]:
    started = time.perf_counter()
    payload = {
        "model": model,
        "prompt": f"{system}\n\n{user}",
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.2,
        },
    }
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        response = client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    elapsed = time.perf_counter() - started
    text = (data.get("response") or "").strip()
    return text, elapsed, data


def json_valid(text: str) -> bool:
    try:
        parsed = json.loads(text)
    except Exception:
        return False
    required = {"tension_level", "state_delta", "game_events"}
    return isinstance(parsed, dict) and required.issubset(parsed.keys())


def run_single_model_case(case: Case, model: str) -> dict:
    durations: list[float] = []
    lengths: list[int] = []
    json_scores: list[bool] = []
    last_text = ""
    failures = 0

    for _ in range(RUNS_PER_CASE):
        try:
            text, elapsed, _raw = call_ollama(
                model=model,
                system=case.system,
                user=case.user,
                max_tokens=case.max_tokens,
            )
            durations.append(elapsed)
            lengths.append(len(text))
            if case.expects_json:
                json_scores.append(json_valid(text))
            last_text = text
        except Exception as exc:
            failures += 1
            last_text = f"<erro: {exc}>"

    return {
        "durations": durations,
        "lengths": lengths,
        "json_scores": json_scores,
        "last_text": last_text,
        "failures": failures,
    }


def print_model_case_result(case: Case, model: str, result: dict) -> None:
    durations = result["durations"]
    failures = result["failures"]
    last_text = str(result["last_text"])

    if not durations:
        print(f"- {model}: falhou em todas as execuÃ§Ãµes ({failures}/{RUNS_PER_CASE})")
        print(f"  preview: {last_text[:180]}")
        return

    lengths = result["lengths"]
    avg_s = statistics.mean(durations)
    p95_s = max(durations)
    avg_len = int(statistics.mean(lengths))
    print(
        f"- {model}: avg={avg_s:.2f}s p95={p95_s:.2f}s avg_chars={avg_len} failures={failures}",
        end="",
    )
    if case.expects_json:
        json_scores = result["json_scores"]
        rate = 100.0 * (sum(json_scores) / len(json_scores)) if json_scores else 0.0
        print(f" json_valid={rate:.0f}%")
    else:
        print()

    preview = " ".join(last_text.split())[:180]
    print(f"  preview: {preview}")


def run_case(case: Case) -> None:
    print(f"## Case: {case.name}")
    for model in MODELS:
        result = run_single_model_case(case, model)
        print_model_case_result(case, model, result)
    print()


def main() -> None:
    print("# Benchmark local models (Fase 2)\n")
    print(f"Models: {', '.join(MODELS)}")
    print(f"Cases: {', '.join(case.name for case in CASES)}")
    print(f"Runs per case: {RUNS_PER_CASE}\n")

    for case in CASES:
        run_case(case)


if __name__ == "__main__":
    main()

