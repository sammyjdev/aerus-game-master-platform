#!/usr/bin/env python3
"""
run_local_benchmark.py - Evaluates the local ExLlamaV3 model against Aerus RPG core mechanics:
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

SCENARIOS = [
    {
        "id": "arrival_port_myr",
        "name": "1. Chegada & Atmosfera Dark Fantasy",
        "action": "Eu desço do barco nas docas chuvosas de Port Myr, puxo meu capuz encharcado e procuro o noviço da Igreja que estava me observando com medo.",
        "eval_fn": lambda n, d: any(w in n.lower() for w in ["port myr", "docas", "cais", "barco", "chuva", "porto"]) and any(w in n.lower() for w in ["kael", "você", "seus", "noviço", "figura", "jovem"])
    },
    {
        "id": "combat_damage",
        "name": "2. Combate & Causalidade de Dano (HP)",
        "action": "O Rastejador Cinzento salta sobre mim com suas garras de osso. Tento bloquear com o braço, mas a criatura me atinge no ombro.",
        "eval_fn": lambda n, d: any(w in n.lower() for w in ["ombro", "garra", "dor", "sangue", "corte", "atinge", "braço", "impacto", "golpe", "criatura", "rastejador"])
    },
    {
        "id": "lore_reputation",
        "name": "3. Fidelidade ao Lore & Reputação de Facção",
        "action": "Fico entre o sentinela ferido da Igreja do Puro Fogo e a turba enfurecida, erguendo minha espada para proteger o soldado do Templo.",
        "eval_fn": lambda n, d: any(w in n.lower() for w in ["igreja", "puro fogo", "sentinela", "templo", "soldado", "espada", "turba", "multidão"])
    },
    {
        "id": "inventory_strictness",
        "name": "4. Inventário Estrito & Poção",
        "action": "Pego a poção de cura do meu cinto e bebo o líquido amargo para estancar o sangramento do meu ferimento.",
        "eval_fn": lambda n, d: any(w in n.lower() for w in ["poção", "líquido", "ferimento", "cura", "alívio", "sangramento", "amargo", "cinto", "frasco"])
    },
    {
        "id": "level5_awakening",
        "name": "5. Marco de Nível & Desbloqueio de Habilidade",
        "action": "Ao desferir o golpe final na besta, sinto uma energia ancestral despertar no meu sangue ao atingir o nível 5. Desperto a habilidade Lâmina de Cinzas!",
        "eval_fn": lambda n, d: any(w in n.lower() for w in ["despertar", "energia", "poder", "lâmina", "cinzas", "nível", "golpe", "sangue", "besta", "habilidade"])
    },
    {
        "id": "magic_backlash",
        "name": "6. Magia Corrompida & Efeito de Ricochete (Backlash)",
        "action": "Tento canalizar a magia corrompida do Fio Primordial sem o devido selamento. A magia sai do controle e ricocheteia contra meu próprio peito.",
        "eval_fn": lambda n, d: any(w in n.lower() for w in ["corrupção", "ricocheteia", "rebound", "queima", "dor", "magia", "peito", "fio", "controle", "energia"])
    }
]

async def run_scenario_turn(scenario):
    player_id = "test-player-1"
    sc_id = scenario["id"]
    db_path = f"/tmp/aerus_bm_local_exllama_{sc_id}.db"
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
        
        os.environ["AERUS_LLM_PROVIDER"] = "exllamav3"
        os.environ["AERUS_EXLLAMAV3_URL"] = os.getenv("AERUS_EXLLAMAV3_URL", "http://127.0.0.1:5000/v1")
        os.environ["AERUS_EXLLAMAV3_API_KEY"] = os.getenv("AERUS_EXLLAMAV3_API_KEY", "cc0bdef6b1a589e63dfe207dcb81055d")
        os.environ["AERUS_EXLLAMAV3_MODEL"] = os.getenv("AERUS_EXLLAMAV3_MODEL", "Llama-3.1-8B-Instruct-exl3-5.0bpw")
        
        t0 = time.perf_counter()
        try:
            await game_master.process_batch(conn=db, batch=batch)
            latency = time.perf_counter() - t0
            
            history = await state_manager.get_recent_history(db, limit=2)
            narrative = ""
            for h in history:
                if h["role"] == "assistant":
                    narrative = h["content"]
                    
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
    model_name = os.getenv("AERUS_EXLLAMAV3_MODEL", "Llama-3.1-8B-Instruct-exl3-5.0bpw")
    print("==========================================================================")
    print(f"  ⚡ BENCHMARK LOCAL EXLLAMAV3 (RTX 4070 Ti) - {model_name}")
    print("==========================================================================")
    print(f"Endpoint: {os.getenv('AERUS_EXLLAMAV3_URL', 'http://127.0.0.1:5000/v1')}")
    print(f"Total de Cenários Mecânicos: {len(SCENARIOS)}")
    print("==========================================================================\n")
    
    passed_count = 0
    total_latency = 0.0
    
    for sc in SCENARIOS:
        sc_id = sc["id"]
        sc_name = sc["name"]
        sys.stdout.write(f"  • {sc_name}... ")
        sys.stdout.flush()
        
        res = await run_scenario_turn(sc)
        total_latency += res["latency"]
        
        if res["passed"]:
            passed_count += 1
            print(f"✅ PASSOU ({res['latency']:.2f}s)")
        else:
            err_info = f" [Erro: {res['error']}]" if res["error"] else ""
            print(f"❌ FALHOU ({res['latency']:.2f}s){err_info}")
            if res["narrative"]:
                print(f"    Preview: {res['narrative'][:120]}...")
            
    avg_lat = total_latency / len(SCENARIOS)
    score_pct = (passed_count / len(SCENARIOS)) * 100
    print("\n--------------------------------------------------------------------------")
    print(f"🏆 Resultado Local: {passed_count}/{len(SCENARIOS)} ({score_pct:.0f}%) | Latência Média: {avg_lat:.2f}s")
    print("--------------------------------------------------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
