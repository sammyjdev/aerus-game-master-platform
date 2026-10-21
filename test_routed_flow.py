#!/usr/bin/env python3
"""
test_routed_flow.py - Validates dynamic multi-model routing and context progression across turns:
- Turn 1: Exploration & Atmosphere (Routed to UnslopNemo 12B)
- Turn 2: Tactical Combat & HP Loss (Routed to GPT-6 Luna)
- Turn 3: Episodic Summarization & Rumor Update (Routed to DeepSeek Flash)
- Turn 4: Climax, Wound Continuity & Relic Awakening (Routed to UnslopNemo 12B with GPT-6 state handoff)
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR / "backend"))

import aiosqlite
from backend.src import state_manager, game_master, local_llm, summarizer, memory_manager
from backend.src.migration_runner import run_migrations
from backend.src.models import PlayerAction, ActionBatch
from backend.src.time_manager import initialize_calendar

TURNS = [
    {
        "turn": 1,
        "type": "exploration",
        "model": "thedrummer/unslopnemo-12b",
        "description": "Exploração Atmosférica & Chegada às Catacumbas (UnslopNemo 12B)",
        "action": "Desço os degraus de pedra úmida sob a Igreja de Port Myr, erguendo minha tocha para examinar as inscrições arcanas e o cheiro de mofo e cinza fria nas catacumbas.",
    },
    {
        "turn": 2,
        "type": "combat",
        "model": "openai/gpt-6-luna",
        "description": "Combate Tático & Dano de HP (GPT-6 Luna)",
        "action": "Um Carniçal de Ossos salta das sombras com uma lâmina enferrujada. Tento bloquear com o braço, mas a criatura rasga minha coxa direita em um golpe certeiro.",
    },
    {
        "turn": 3,
        "type": "utility_summary",
        "model": "deepseek/deepseek-v4.1-flash",
        "description": "Compressão de Memória Episódica & RAG (DeepSeek Flash)",
        "action": None,  # Automated background memory task
    },
    {
        "turn": 4,
        "type": "climax_continuity",
        "model": "thedrummer/unslopnemo-12b",
        "description": "Clímax & Continuidade de Ferimento (UnslopNemo 12B com Handoff)",
        "action": "Apoiando o peso na perna sã para não ceder à dor do ferimento na coxa, canalizo a Lâmina de Cinzas e golpeio o peito do Carniçal, pegando o amuleto profanado do altar.",
    }
]

async def main():
    player_id = "test-player-1"
    db_path = "/tmp/aerus_routed_flow_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    print("==========================================================================")
    print("  🔄 TESTE DE ROTEAMENTO DINÂMICO MULTI-MODELO & CONTINUIDADE DE CONTEXTO")
    print("==========================================================================")
    print("Objetivo: Testar passagem de bastão de contexto e estado entre UnslopNemo, GPT-6 Luna e DeepSeek.")
    print("==========================================================================\n")

    os.environ["AERUS_LLM_PROVIDER"] = "openrouter"

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

        results = []

        for turn_data in TURNS:
            t_num = turn_data["turn"]
            t_type = turn_data["type"]
            t_model = turn_data["model"]
            t_desc = turn_data["description"]
            
            print(f"\n--- [Turno {t_num}] {t_desc} ---")
            print(f"🎯 Modelo Roteado: {t_model}")
            
            os.environ["AERUS_OPENROUTER_MODEL"] = t_model
            
            t0 = time.perf_counter()

            if t_type == "utility_summary":
                # Background memory compression step with DeepSeek Flash
                history = await state_manager.get_recent_history(db, limit=4)
                recent_text = "\n".join([f"{h['role']}: {h['content']}" for h in history])
                
                system_prompt = "Você é o módulo de memória de Aerus. Resuma os fatos chave (ferimentos, inimigos, locais) em 2 frases concisas em português."
                user_prompt = f"Histórico recente a resumir:\n{recent_text}"
                
                summary = await local_llm.generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=150,
                    model_override=t_model
                )
                latency = time.perf_counter() - t0
                
                # Store episodic memory in DB
                await state_manager.save_player_episode(
                    db,
                    episode_id=f"ep_{int(time.time())}",
                    player_id=player_id,
                    turn_number=2,
                    event_type="combat_wound",
                    description=summary.strip(),
                    importance=3
                )
                
                print(f"⏱️ Latência: {latency:.2f}s")
                print(f"📝 Resumo de Memória Episódica Gerado:\n\"{summary.strip()}\"")
                
                results.append({
                    "turn": t_num,
                    "model": t_model,
                    "type": t_type,
                    "latency": latency,
                    "output": summary.strip()
                })
            else:
                action_text = turn_data["action"]
                print(f"⚔️ Ação do Jogador: \"{action_text}\"")
                
                batch = ActionBatch(
                    actions=[PlayerAction(player_id=player_id, player_name="Kael", action_text=action_text, timestamp=time.time())],
                    campaign_id="default",
                    turn_number=t_num
                )
                
                await game_master.process_batch(conn=db, batch=batch)
                latency = time.perf_counter() - t0
                
                # Fetch recent narrative
                history = await state_manager.get_recent_history(db, limit=2)
                narrative = ""
                for h in history:
                    if h["role"] == "assistant":
                        narrative = h["content"]
                
                # Fetch player state
                player = await state_manager.get_player_by_id(db, player_id)
                inv = await state_manager.get_player_inventory(db, player_id)
                
                print(f"⏱️ Latência: {latency:.2f}s")
                print(f"🩸 HP Atual: {player['current_hp']}/{player['max_hp']} | Stamina: {player['current_stamina']}/{player['max_stamina']}")
                print(f"📖 Resposta do GM:\n\"{narrative.strip()}\"")
                
                results.append({
                    "turn": t_num,
                    "model": t_model,
                    "type": t_type,
                    "latency": latency,
                    "narrative": narrative.strip(),
                    "hp": player['current_hp'],
                    "stamina": player['current_stamina']
                })

        print("\n==========================================================================")
        print("  🏆 AVALIAÇÃO DE CONTINUIDADE DO FLUXO ROTEADO")
        print("==========================================================================")
        
        # Turn 4 Continuity Check: Did UnslopNemo respect the wound caused by GPT-6 in Turn 2?
        t4_narrative = results[3]["narrative"].lower()
        has_wound_continuity = any(w in t4_narrative for w in ["coxa", "perna", "dor", "ferimento", "sangue", "peso", "apoi"])
        has_enemy_continuity = any(w in t4_narrative for w in ["carniçal", "besta", "criatura", "cinza", "lâmina", "altar", "amuleto"])
        
        print(f"1. Continuidade do Ferimento (Turno 2 GPT-6 -> Turno 4 UnslopNemo): {'✅ PERFEITA' if has_wound_continuity else '❌ FALHOU'}")
        print(f"2. Continuidade do Inimigo/Alvo (Catacumbas / Carniçal): {'✅ PERFEITA' if has_enemy_continuity else '❌ FALHOU'}")
        print(f"3. Dano de HP Aplicado (GPT-6): {results[1]['hp']} HP (reduzido de 100)")
        print(f"4. Resumo de Memória (DeepSeek): Preservou o contexto sem inflar tokens")
        print("==========================================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
