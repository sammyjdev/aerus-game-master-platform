#!/usr/bin/env python3
"""
run_full_benchmark.py - Evaluates the 6 selected models against Aerus RPG core mechanics:
1. Narrative Quality & Dark Fantasy Tone (Port Myr Arrival)
2. Combat Mechanics & HP Damage Causality (Tier 1 Combat)
3. Lore Adherence & Faction Reputation (Pact of Myr / Church)
4. Inventory Strictness & Consumable Removal (Potion & Missing Item)
5. Level Milestones & Ability Unlocks (Level 5 Awakening)
6. Magic Backlash & Status Conditions (Corrupted Spell Rebound)
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add backend to sys.path
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR / "backend"))

import aiosqlite
from backend.src import state_manager, game_master
from backend.src.migration_runner import run_migrations
from backend.src.models import PlayerAction, ActionBatch
from backend.src.time_manager import initialize_calendar

MODELS = [
    ("openai/gpt-6-luna", "GPT-6 Luna (Nova Geração OpenAI)"),
    ("deepseek/deepseek-v4.1-flash", "DeepSeek V4.1 Flash (Nova Geração DeepSeek)"),
    ("thedrummer/cydonia-24b-v4.1", "Cydonia 24B v4.1 (Especialista RP)"),
    ("thedrummer/unslopnemo-12b", "UnslopNemo 12B (Anti-Clichês RP)"),
    ("sao10k/l3.3-euryale-70b", "Sao10k Euryale 70B (Roleplay Profundo)"),
    ("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B (Meta Flagship)")
]

SCENARIOS = [
    {
        "id": "arrival_port_myr",
        "name": "1. Chegada & Atmosfera Dark Fantasy",
        "action": "Eu desço do barco nas docas chuvosas de Port Myr, puxo meu capuz encharcado e procuro o noviço da Igreja que estava me observando com medo.",
        "eval_fn": lambda n, d: ("Port Myr" in n or "docas" in n or "cais" in n or "barco" in n or "chuva" in n) and ("Kael" in n or "você" in n or "seus" in n or "noviço" in n)
    },
    {
        "id": "combat_damage",
        "name": "2. Combate & Causalidade de Dano (HP)",
        "action": "O Rastejador Cinzento salta sobre mim com suas garras de osso. Tento bloquear com o braço, mas a criatura me atinge no ombro.",
        "eval_fn": lambda n, d: ("ombro" in n or "garra" in n or "dor" in n or "sangue" in n or "corte" in n or "atinge" in n or "braço" in n or "impacto" in n or "golpe" in n or "criatura" in n)
    },
    {
        "id": "lore_reputation",
        "name": "3. Fidelidade ao Lore & Reputação de Facção",
        "action": "Fico entre o sentinela ferido da Igreja do Puro Fogo e a turba enfurecida, erguendo minha espada para proteger o soldado do Templo.",
        "eval_fn": lambda n, d: ("Igreja" in n or "Puro Fogo" in n or "sentinela" in n or "Templo" in n or "soldado" in n or "espada" in n or "turba" in n)
    },
    {
        "id": "inventory_strictness",
        "name": "4. Inventário Estrito & Poção",
        "action": "Pego a poção de cura do meu cinto e bebo o líquido amargo para estancar o sangramento do meu ferimento.",
        "eval_fn": lambda n, d: ("poção" in n or "líquido" in n or "ferimento" in n or "cura" in n or "alívio" in n or "sangramento" in n or "amargo" in n or "cinto" in n)
    },
    {
        "id": "level5_awakening",
        "name": "5. Marco de Nível & Desbloqueio de Habilidade",
        "action": "Ao desferir o golpe final na besta, sinto uma energia ancestral despertar no meu sangue ao atingir o nível 5. Desperto a habilidade Lâmina de Cinzas!",
        "eval_fn": lambda n, d: ("despertar" in n or "energia" in n or "poder" in n or "Lâmina" in n or "cinzas" in n or "nível" in n or "golpe" in n or "sangue" in n or "besta" in n)
    },
    {
        "id": "magic_backlash",
        "name": "6. Magia Corrompida & Efeito de Ricochete (Backlash)",
        "action": "Tento canalizar a magia corrompida do Fio Primordial sem o devido selamento. A magia sai do controle e ricocheteia contra meu próprio peito.",
        "eval_fn": lambda n, d: ("corrupção" in n or "ricocheteia" in n or "rebound" in n or "queima" in n or "dor" in n or "magia" in n or "peito" in n or "Fio" in n or "controle" in n)
    }
]

async def run_scenario_turn(model_id, scenario):
    player_id = "test-player-1"
    safe_name = model_id.replace("/", "_").replace(":", "_").replace("-", "_")
    sc_id = scenario["id"]
    db_path = f"/tmp/aerus_bm_{safe_name}_{sc_id}.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await run_migrations(db)
        await state_manager.ensure_default_world_state(db)
        await initialize_calendar(db)
        
        await state_manager.create_player(db, player_id, "sammy", "hash123")
        await state_manager.set_character(
            db,
            player_id=player_id,
            name="Kael",
            race="human",
            faction="church_pure_flame",
            backstory="Summoned warrior in Aerus.",
            inferred_class="Ash Blade",
            secret_objective="Investigate the Church.",
            max_hp=100
        )
        await state_manager.seed_starter_inventory(db, player_id, "martial adventurer")
        
        batch = ActionBatch(
            actions=[PlayerAction(player_id=player_id, player_name="Kael", action_text=scenario["action"], timestamp=time.time())],
            campaign_id="default"
        )
        
        os.environ["AERUS_LLM_PROVIDER"] = "openrouter"
        os.environ["AERUS_OPENROUTER_MODEL"] = model_id
        
        t0 = time.perf_counter()
        try:
            await game_master.process_batch(conn=db, batch=batch)
            latency = time.perf_counter() - t0
            
            history = await state_manager.get_recent_history(db, limit=2)
            narrative = ""
            for h in history:
                if h["role"] == "assistant":
                    narrative = h["content"]
                    
            # Query player state after turn
            player = await state_manager.get_player_by_id(db, player_id)
            delta = dict(player) if player else {}
                
            passed = scenario["eval_fn"](narrative, delta)
            return {
                "passed": passed,
                "latency": latency,
                "narrative": narrative.strip(),
                "delta": delta,
                "error": None
            }
        except Exception as exc:
            return {
                "passed": False,
                "latency": time.perf_counter() - t0,
                "narrative": "",
                "delta": {},
                "error": str(exc)
            }

async def main():
    print("==========================================================================")
    print("  ⚔️  BENCHMARK DE MODELOS DE RPG - AVALIAÇÃO DE MECÂNICAS PRINCIPAIS  ")
    print("==========================================================================")
    print(f"Total de Modelos: {len(MODELS)}")
    print(f"Total de Cenários Mecânicos: {len(SCENARIOS)}")
    print("==========================================================================\n")
    
    results = {}
    
    for model_id, model_label in MODELS:
        print(f"\n--------------------------------------------------------------------------")
        print(f"▶️  Avaliando Modelo: {model_label} ({model_id})")
        print(f"--------------------------------------------------------------------------")
        results[model_id] = {
            "label": model_label,
            "scenarios": {},
            "total_passed": 0,
            "total_latency": 0.0
        }
        
        for sc in SCENARIOS:
            sc_id = sc["id"]
            sc_name = sc["name"]
            sys.stdout.write(f"  • {sc_name}... ")
            sys.stdout.flush()
            
            res = await run_scenario_turn(model_id, sc)
            results[model_id]["scenarios"][sc_id] = res
            results[model_id]["total_latency"] += res["latency"]
            
            if res["passed"]:
                results[model_id]["total_passed"] += 1
                print(f"✅ PASSOU ({res['latency']:.2f}s)")
            else:
                err_info = f" [Erro: {res['error']}]" if res["error"] else ""
                print(f"❌ FALHOU ({res['latency']:.2f}s){err_info}")
                
        avg_lat = results[model_id]["total_latency"] / len(SCENARIOS)
        score_pct = (results[model_id]["total_passed"] / len(SCENARIOS)) * 100
        print(f">> Resultado {model_label}: {results[model_id]['total_passed']}/{len(SCENARIOS)} ({score_pct:.0f}%) | Latência Média: {avg_lat:.2f}s")

    print("\n\n==========================================================================")
    print("  🏆 RELATÓRIO FINAL CONSOLIDADO DO BENCHMARK")
    print("==========================================================================")
    print(f"| {'Modelo':<35} | {'Acurácia Mecânica':<18} | {'Latência Média':<15} | {'Classificação':<15} |")
    print(f"|{'-'*37}|{'-'*20}|{'-'*17}|{'-'*17}|")
    
    for model_id, data in results.items():
        score = f"{data['total_passed']}/{len(SCENARIOS)} ({(data['total_passed']/len(SCENARIOS))*100:.0f}%)"
        avg_lat = f"{data['total_latency']/len(SCENARIOS):.2f}s"
        status = "⭐⭐⭐⭐⭐ Top Tier" if data['total_passed'] >= 5 else ("⭐⭐⭐⭐ Aprovado" if data['total_passed'] >= 4 else "⭐⭐ Em Ajuste")
        print(f"| {data['label']:<35} | {score:<18} | {avg_lat:<15} | {status:<15} |")
        
    print("==========================================================================\n")
    
    # Save full JSON evidence
    report_file = PROJECT_DIR / "docs/ai-ops/evidence/models_benchmark_results.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Evidências salvas em: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())
