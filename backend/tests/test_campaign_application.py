"""Application campaign boundaries with real persistence and socket serialization."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from tests.test_action_queue import queue_run
from src import context_builder, game_master, main, state_manager
from src.models import ActionBatch, PlayerAction


@pytest_asyncio.fixture
async def campaigns(db, queue_run):
    run = queue_run
    await db.execute("UPDATE players SET campaign_id = ? WHERE player_id = ?", ("campA", run.player_id))
    await state_manager.create_player(db, "player-b", "player-b", "test-hash")
    await state_manager.set_character(
        db, player_id="player-b", name="PlayerBeta", race="human",
        faction="guild_of_threads", backstory="A separate traveler.",
        inferred_class="Traveler", secret_objective="", max_hp=100,
    )
    await db.execute("UPDATE players SET campaign_id = 'campB' WHERE player_id = 'player-b'")
    await db.commit()
    manager = game_master.cm.manager
    manager.disconnect(run.player_id)
    run.socket_a = SimpleNamespace(accept=AsyncMock(), send_text=AsyncMock())
    run.socket_b = SimpleNamespace(accept=AsyncMock(), send_text=AsyncMock())
    await manager.connect(run.socket_a, run.player_id, "queue-player", campaign_id="campA")
    await manager.connect(run.socket_b, "player-b", "player-b", campaign_id="campB")
    return run


def batch_for(player_id, name, campaign_id):
    batch = ActionBatch(actions=[PlayerAction(player_id, name, "Wait by the gate.", 0)], turn_number=1)
    batch.campaign_id = campaign_id
    return batch


@pytest.mark.asyncio
async def test_context_excludes_other_campaign_party(db, campaigns):
    context = await context_builder.build_context(db, batch_for(campaigns.player_id, "Queue Player", "campA"))
    assert "Queue Player" in context.l2_state
    assert "PlayerBeta" not in context.l2_state


@pytest.mark.asyncio
async def test_player_dice_broadcast_ignores_client_campaign_spoof(campaigns):
    request = SimpleNamespace(json=AsyncMock(return_value={"die": 20, "campaign_id": "campB"}))
    await main.roll_dice(request, {"player_id": campaigns.player_id})
    assert campaigns.socket_a.send_text.await_count == 1
    assert campaigns.socket_b.send_text.await_count == 0
    payload = json.loads(campaigns.socket_a.send_text.call_args.args[0])
    assert payload["type"] == "dice_result"
    assert payload["player_id"] == campaigns.player_id


@pytest.mark.asyncio
async def test_campaign_b_drains_while_campaign_a_generation_is_blocked(db, campaigns, monkeypatch):
    run = campaigns
    second_started = asyncio.Event()
    generate = game_master.local_llm.generate_chat

    async def observed_generate(messages, **kwargs):
        if "PlayerBeta" in messages[-1]["content"]:
            second_started.set()
        return await generate(messages, **kwargs)

    monkeypatch.setattr(game_master.local_llm, "generate_chat", observed_generate)
    await game_master.submit_action(run.player_id, "Queue Player", "A waits.")
    await asyncio.wait_for(run.started.wait(), timeout=5)
    try:
        await game_master.submit_action("player-b", "PlayerBeta", "B waits.")
        await asyncio.wait_for(second_started.wait(), timeout=5)
    finally:
        run.release.set()

    # Await all recorded consumers rather than use a wall-clock sleep.
    tasks = {task for task, _ in run.calls}
    await asyncio.wait_for(asyncio.gather(*tasks), timeout=5)
    assert len(tasks) == 2
    assert all(not ("A waits." in text and "B waits." in text) for _, text in run.calls)


@pytest.mark.asyncio
async def test_mixed_internal_batch_rejected_before_provider_or_broadcast(db, campaigns):
    batch = batch_for(campaigns.player_id, "Queue Player", "campA")
    batch.actions.append(PlayerAction("player-b", "PlayerBeta", "B waits.", 0))
    campaigns.release.set()
    with pytest.raises(ValueError, match="campaign"):
        await game_master.process_batch(db, batch)
    assert campaigns.calls == []
    assert campaigns.socket_a.send_text.await_count == 0
    assert campaigns.socket_b.send_text.await_count == 0
    assert await state_manager.get_recent_history(db) == []


async def seed_owned_state(db, run):
    from src import time_manager

    for campaign_id, marker, player_id, turn in [
        ("campA", "ALPHA_ONLY", run.player_id, 4),
        ("campB", "BETA_ONLY", "player-b", 9),
    ]:
        await state_manager.ensure_default_world_state(db, campaign_id=campaign_id)
        await state_manager.set_world_state(db, "current_location", marker, campaign_id=campaign_id)
        await state_manager.set_world_state(db, "tension_level", "7", campaign_id=campaign_id)
        await state_manager.set_quest_flag(db, "ownership_marker", marker, campaign_id=campaign_id)
        await state_manager.append_history(db, marker, turn, "user", marker + " history", campaign_id=campaign_id)
        await state_manager.upsert_world_memory(db, marker + " world", campaign_id=campaign_id)
        await state_manager.upsert_arc_memory(db, marker + " arc", campaign_id=campaign_id)
        await state_manager.upsert_character_memory(db, player_id, marker + " character")
        await state_manager.save_player_episode(db, marker, player_id, turn, "social_action", marker + " episode", 3)
        await time_manager.initialize_calendar(db, campaign_id=campaign_id)
        await time_manager.advance_days(db, 2 if campaign_id == "campA" else 12, campaign_id=campaign_id)
        await state_manager.apply_state_delta(db, player_id, {
            "conditions_add": [{"name": "burning", "duration_turns": 2, "applied_at_turn": 0}],
        })


async def snapshot_b(db):
    snapshot = {}
    for table in ["world_state", "quest_flags", "history", "world_memory", "arc_memory"]:
        snapshot[table] = [tuple(row) for row in await db.execute_fetchall(
            f"SELECT * FROM {table} WHERE campaign_id = ? ORDER BY rowid", ("campB",)
        )]
    for table in ["players", "inventory", "conditions", "character_memory", "player_episodes", "faction_reputation"]:
        snapshot[table] = [tuple(row) for row in await db.execute_fetchall(
            f"SELECT * FROM {table} WHERE player_id = ? ORDER BY rowid", ("player-b",)
        )]
    return snapshot


def messages(socket):
    return [json.loads(call.args[0]) for call in socket.send_text.call_args_list]


@pytest.mark.asyncio
async def test_real_context_memory_and_summary_exclude_foreign_resources(db, campaigns, monkeypatch):
    from src import memory_manager, summarizer
    from src.models import GMResponse

    run = campaigns
    await seed_owned_state(db, run)
    before = await snapshot_b(db)
    batch = batch_for(run.player_id, "Queue Player", "campA")
    context = await context_builder.build_context(db, batch)
    assert "ALPHA_ONLY" in context.to_system_prompt()
    assert "BETA_ONLY" not in context.to_system_prompt()
    assert await game_master._get_party_size(db, batch) == 1
    transcript = await memory_manager._build_memory_transcript(db, batch, GMResponse(narrative="Alpha arrival"))
    assert "ALPHA_ONLY history" in transcript
    assert "BETA_ONLY" not in transcript
    summary_inputs = []

    async def summarize(system, text, **kwargs):
        summary_inputs.append(text)
        return "ALPHA_ONLY summary"

    monkeypatch.setattr(summarizer, "generate_text", summarize)
    await memory_manager.update_memory_after_turn(db, batch, GMResponse(narrative="Alpha arrival"))
    memory = await state_manager.get_memory_layers(db, [run.player_id], campaign_id="campA")
    assert "ALPHA_ONLY summary" in memory.world
    assert "ALPHA_ONLY summary" in memory.arc
    assert "ALPHA_ONLY summary" in memory.character
    assert "ALPHA_ONLY history" in summary_inputs[0]
    assert "BETA_ONLY" not in summary_inputs[0]
    assert await snapshot_b(db) == before
    with pytest.raises(ValueError, match="campaign"):
        await memory_manager.update_memory_after_turn(db, batch, GMResponse(narrative="", game_events=[{"type": "DEATH", "player_id": "player-b"}]))
    assert await snapshot_b(db) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("branch", ["local", "standard", "slm", "hosted"])
@pytest.mark.parametrize("foreign_target", [False, True])
async def test_all_narrator_branches_scope_state_memory_and_serialized_messages(db, campaigns, monkeypatch, branch, foreign_target):
    from openai.types.chat import ChatCompletionChunk
    from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

    run = campaigns
    await seed_owned_state(db, run)
    before = await snapshot_b(db)
    target = "player-b" if foreign_target else run.player_id
    state = {
        "state_delta": {target: {"hp_change": -1}},
        "game_events": [{"type": "LOOT", "player_id": target}],
        "dice_rolls": [], "tension_level": 7, "audio_cue": "boss_music",
    }
    structured = "Alpha narration.\n<game_state>" + json.dumps(state) + "</game_state>"
    monkeypatch.setenv("AERUS_LOCAL_ONLY", "true" if branch == "local" else "false")
    monkeypatch.setenv("SLM_ENABLED", "true" if branch == "slm" else "false")
    monkeypatch.setenv("HOSTED_NARRATOR_ENABLED", "true" if branch == "hosted" else "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    provider_inputs = []

    async def generate_chat(input_messages, **kwargs):
        provider_inputs.append(input_messages)
        return structured

    async def completion(**kwargs):
        provider_inputs.append(kwargs["messages"])

        async def chunks():
            yield ChatCompletionChunk(
                id="test", created=0, model="test", object="chat.completion.chunk",
                choices=[Choice(index=0, delta=ChoiceDelta(content=structured if branch == "standard" else "Alpha narration."))],
            )
        return chunks()

    monkeypatch.setattr(game_master.local_llm, "generate_chat", generate_chat)
    monkeypatch.setattr(game_master.local_llm, "generate_text", AsyncMock(return_value=json.dumps(state)))
    monkeypatch.setattr(game_master, "AsyncOpenAI", lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion))))
    monkeypatch.setattr(game_master.hosted_narrator, "narrate", AsyncMock(return_value={"text": "Alpha narration."}))
    monkeypatch.setattr(game_master.vector_store, "_narration_collection", None)
    batch = batch_for(run.player_id, "Queue Player", "campA")
    batch.turn_number = 5
    await game_master.process_batch(db, batch)

    assert messages(run.socket_b) == []
    assert await snapshot_b(db) == before
    outbound = messages(run.socket_a)
    assert any(message["type"] == "narrative_token" for message in outbound)
    if foreign_target:
        assert any(message["type"] == "error" for message in outbound)
        assert await state_manager.get_current_turn_number(db, campaign_id="campA") == 4
    else:
        assert {"stream_end", "state_update", "audio_cue", "boss_music"}.issubset({m["type"] for m in outbound})
        assert any(m["type"] == "game_event" and m["event"] == "COOP_MISSION" for m in outbound)
        assert await state_manager.get_current_turn_number(db, campaign_id="campA") == 5
        memory = await state_manager.get_memory_layers(db, [run.player_id], campaign_id="campA")
        assert "BETA_ONLY" not in memory.world + memory.arc + memory.character
    for provider_messages in provider_inputs:
        assert "BETA_ONLY" not in json.dumps(provider_messages)
        assert "PlayerBeta" not in json.dumps(provider_messages)


@pytest.mark.asyncio
async def test_http_history_debug_admin_sync_and_spoofing_use_stored_campaign(db, campaigns, monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from src.auth import create_token

    run = campaigns
    await seed_owned_state(db, run)
    monkeypatch.setenv("ADMIN_SECRET", "test-admin-secret")
    headers = {"Authorization": "Bearer " + create_token(run.player_id, "queue-player")}
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        history = await client.get("/game/history?campaign_id=campB", headers=headers)
        assert history.status_code == 200
        assert "ALPHA_ONLY" in history.text and "BETA_ONLY" not in history.text
        debug = await client.get("/debug/state?campaign_id=campB", headers=headers)
        assert debug.status_code == 200
        data = debug.json()
        assert data["world_state"]["current_location"] == "ALPHA_ONLY"
        assert data["runtime"]["players_rows"] == 1
        assert data["runtime"]["history_rows"] == 1
        assert data["runtime"]["connected_player_ids"] == [run.player_id]
        assert "BETA_ONLY" not in debug.text
        result = await client.put("/character/backstory", headers=headers, json={"backstory": "An old traveler returns to the distant harbor after many years away.", "campaign_id": "campB"})
        assert result.status_code == 200
        assert messages(run.socket_b) == []
        run.socket_a.send_text.reset_mock()
        update = await client.patch("/admin/players/player-b", headers={"X-Admin-Secret": "test-admin-secret"}, json={"name": "Beta Updated"})
        assert update.status_code == 200
        assert messages(run.socket_a) == []
        assert messages(run.socket_b)[-1]["world_state"]["current_location"] == "BETA_ONLY"


@pytest.mark.asyncio
async def test_gm_dice_requires_existing_admin_and_player_can_only_submit_own_roll(db, campaigns, monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from src.auth import create_token

    run = campaigns
    monkeypatch.setenv("ADMIN_SECRET", "test-admin-secret")
    player_headers = {"Authorization": "Bearer " + create_token(run.player_id, "queue-player")}
    request_body = {"player_id": "player-b", "roll_type": "attack", "dc": 10, "description": "Beta test"}
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        unauthorized = await client.post("/gm/dice/request", headers=player_headers, json=request_body)
        assert unauthorized.status_code == 403
        assert messages(run.socket_b) == []
        requested = await client.post("/gm/dice/request", headers={"X-Admin-Secret": "test-admin-secret"}, json=request_body)
        assert requested.status_code == 200
        roll_id = requested.json()["roll_id"]
        assert messages(run.socket_a) == []
        assert messages(run.socket_b)[-1]["type"] == "request_dice_roll"
        foreign_submit = await client.post("/dice/submit", headers=player_headers, json={"roll_id": roll_id, "initial_roll": 12, "initial_result": 12, "argument": "foreign"})
        assert foreign_submit.status_code == 400
        unauthorized_resolve = await client.post("/gm/dice/resolve", headers=player_headers, json={"roll_id": roll_id, "verdict": "accept_no_bonus"})
        assert unauthorized_resolve.status_code == 403
        requested_a = await client.post("/gm/dice/request", headers={"X-Admin-Secret": "test-admin-secret"}, json={**request_body, "player_id": run.player_id})
        roll_a = requested_a.json()["roll_id"]
        run.socket_a.send_text.reset_mock(); run.socket_b.send_text.reset_mock()
        own = await client.post("/dice/submit", headers=player_headers, json={"roll_id": roll_a, "initial_roll": 12, "initial_result": 12, "argument": "own", "campaign_id": "campB"})
        assert own.status_code == 200
        assert messages(run.socket_b) == []
        assert messages(run.socket_a) == []
        resolved = await client.post("/gm/dice/resolve", headers={"X-Admin-Secret": "test-admin-secret"}, json={"roll_id": roll_a, "verdict": "accept_no_bonus"})
        assert resolved.status_code == 200
        assert messages(run.socket_a)[-1]["type"] == "dice_roll_resolved"


@pytest.mark.asyncio
async def test_reconnect_sync_includes_only_own_history_world_and_offline_roster(db, campaigns):
    from src.auth import create_token

    run = campaigns
    await seed_owned_state(db, run)
    await state_manager.create_player(db, "offline-a", "offline-a", "test-hash")
    await state_manager.set_character(db, "offline-a", "Offline Alpha", "human", "guild_of_threads", "A quiet companion.", "Traveler", "", 100)
    await db.execute("UPDATE players SET campaign_id = 'campA', convocation_sent = 1 WHERE player_id = 'offline-a'")
    await db.execute("UPDATE players SET convocation_sent = 1 WHERE player_id = ?", (run.player_id,))
    await db.commit()
    await main._post_connect_setup(run.player_id, "queue-player", create_token(run.player_id, "queue-player"), "campB")
    outbound = messages(run.socket_a)
    state = next(m for m in outbound if m["type"] == "full_state_sync")
    assert state["world_state"]["current_location"] == "ALPHA_ONLY"
    assert state["roster"] == [pytest.approx(state["roster"][0])] if False else state["roster"]
    assert len(state["roster"]) == 1
    assert state["roster"][0]["player_id"] == "offline-a"
    assert state["roster"][0]["online"] is False
    history = next(m for m in outbound if m["type"] == "history_sync")
    assert history["entries"][0]["content"] == "ALPHA_ONLY history"
    assert "BETA_ONLY" not in json.dumps(outbound)
    assert messages(run.socket_b) == []


@pytest.mark.asyncio
async def test_deleted_player_and_spoofed_ws_campaign_cannot_enqueue(db, campaigns):
    run = campaigns
    await main._handle_ws_message({"action": "Wait.", "campaign_id": "campB"}, run.player_id, "queue-player")
    assert "campB" not in game_master._pending_actions
    await db.execute("DELETE FROM players WHERE player_id = ?", (run.player_id,))
    await db.commit()
    with pytest.raises(ValueError, match="campaign"):
        await game_master.submit_action(run.player_id, "queue-player", "Deleted action")
    socket = SimpleNamespace(close=AsyncMock(), accept=AsyncMock())
    from src.auth import create_token
    await main.websocket_endpoint(socket, create_token("missing-player", "missing"))
    socket.close.assert_awaited_once_with(code=4001, reason="Invalid player")
    socket.accept.assert_not_awaited()
    assert messages(run.socket_b) == []


@pytest.mark.asyncio
async def test_admin_player_detail_uses_player_campaign_world_state(db, campaigns, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    run = campaigns
    await seed_owned_state(db, run)
    monkeypatch.setenv("ADMIN_SECRET", "test-admin-secret")
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        resp = await client.get("/admin/players/player-b", headers={"X-Admin-Secret": "test-admin-secret"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["world_state"]["current_location"] == "BETA_ONLY"
