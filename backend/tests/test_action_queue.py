"""Exercise the scheduler with real SQLite and provider/transport boundaries."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src import game_master, memory_manager, state_manager, summarizer, vector_store
from src.connection_manager import ConnectionManager


@pytest_asyncio.fixture
async def queue_run(db, tmp_path, monkeypatch):
    player_id = "queue-player"
    await state_manager.create_player(db, player_id, "queue-player", "test-hash")
    await state_manager.set_character(
        db, player_id=player_id, name="Queue Player", race="human",
        faction="guild_of_threads", backstory="A patient traveler.",
        inferred_class="Traveler", secret_objective="", max_hp=100,
    )
    run = SimpleNamespace(
        player_id=player_id, started=asyncio.Event(), release=asyncio.Event(),
        provider_returned=asyncio.Event(), consumer_waiting=asyncio.Event(),
        submitter_waiting=asyncio.Event(), initial_waiting=asyncio.Event(),
        calls=[], connections=[], fail_summary=False, summaries=0,
    )

    class ObservedLock(asyncio.Lock):
        async def acquire(self):
            if asyncio.current_task() is game_master._batch_task:
                run.initial_waiting.set()
                if run.provider_returned.is_set():
                    run.consumer_waiting.set()
            else:
                run.submitter_waiting.set()
            return await super().acquire()

    monkeypatch.setattr(game_master, "_pending_actions", [])
    monkeypatch.setattr(game_master, "_batch_task", None)
    monkeypatch.setattr(game_master, "_batch_lock", ObservedLock())
    monkeypatch.setattr(game_master, "_BATCH_WINDOW_SECONDS", 0)
    monkeypatch.setenv("AERUS_LOCAL_ONLY", "true")
    monkeypatch.setattr(vector_store, "CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setattr(vector_store, "_client", None)
    monkeypatch.setattr(vector_store, "_collection", None)

    manager = ConnectionManager()
    websocket = SimpleNamespace(accept=AsyncMock(), send_text=AsyncMock())
    await manager.connect(websocket, player_id, "queue-player")
    monkeypatch.setattr(game_master.cm, "manager", manager)
    original_broadcast = manager.broadcast

    async def broadcast(message, **kwargs):
        if run.fail_summary and message.get("type") == "error":
            raise RuntimeError("Injected error transport failure")
        await original_broadcast(message, **kwargs)

    monkeypatch.setattr(manager, "broadcast", broadcast)

    async def generate_chat(messages, **kwargs):
        assert not game_master._batch_lock.locked()
        run.calls.append((asyncio.current_task(), messages[-1]["content"]))
        if len(run.calls) == 1:
            run.started.set()
            await run.release.wait()
            run.provider_returned.set()
        return (
            f"Narrative {len(run.calls)}.\n<game_state>"
            + json.dumps({"state_delta": {}, "game_events": [], "dice_rolls": [],
                          "tension_level": 4, "audio_cue": ""})
            + "</game_state>"
        )

    async def summarize(*args, **kwargs):
        run.summaries += 1
        if run.fail_summary and run.summaries == 1:
            raise RuntimeError("Injected summary provider failure")
        return "The travelers waited."

    monkeypatch.setattr(game_master.local_llm, "generate_chat", generate_chat)
    monkeypatch.setattr(memory_manager, "generate_text", AsyncMock(return_value="{}"))
    monkeypatch.setattr(summarizer, "generate_text", summarize)
    original_db_context = state_manager.db_context

    @asynccontextmanager
    async def observed_db_context():
        assert not game_master._batch_lock.locked()
        async with original_db_context() as conn:
            run.connections.append(conn)
            yield conn

    monkeypatch.setattr(state_manager, "db_context", observed_db_context)
    try:
        yield run
    finally:
        task = game_master._batch_task
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        game_master._pending_actions.clear()
        client = vector_store._client
        if client is not None:
            client._system.stop()


async def submit(run, text):
    await game_master.submit_action(run.player_id, "Queue Player", text)


async def finish(task):
    await asyncio.wait_for(asyncio.shield(task), timeout=5)


async def assert_connections_closed(run):
    for conn in run.connections:
        with pytest.raises(ValueError, match="no active connection"):
            await conn.execute("SELECT 1")


@pytest.mark.asyncio
@pytest.mark.parametrize("late_count", [1, 3])
async def test_actions_arriving_during_generation_drain_without_trigger(db, queue_run, late_count):
    run = queue_run
    await submit(run, "First: wait by the gate.")
    consumer = game_master._batch_task
    await asyncio.wait_for(run.started.wait(), timeout=5)
    late_actions = [f"Late {index}: wait by the gate." for index in range(late_count)]
    for text in late_actions:
        await submit(run, text)
        assert game_master._batch_task is consumer
    run.release.set()
    await finish(consumer)

    history = await state_manager.get_recent_history(db)
    assert [row["turn_number"] for row in history] == [1, 1, 2, 2]
    user_content = [row["content"] for row in history if row["role"] == "user"]
    assert "First: wait by the gate." in user_content[0]
    assert all(user_content[1].count(text) == 1 for text in late_actions)
    assert [user_content[1].index(text) for text in late_actions] == sorted(
        user_content[1].index(text) for text in late_actions
    )
    assert len(run.calls) == 2
    assert all(task is consumer for task, _ in run.calls)
    assert game_master.get_runtime_metrics()["pending_actions"] == 0
    assert game_master._batch_task is None
    await assert_connections_closed(run)


@pytest.mark.asyncio
async def test_actions_in_initial_window_share_one_batch(db, queue_run):
    run = queue_run
    await submit(run, "First: wait by the gate.")
    consumer = game_master._batch_task
    await submit(run, "Second: wait by the gate.")
    await asyncio.wait_for(run.started.wait(), timeout=5)
    run.release.set()
    await finish(consumer)

    history = await state_manager.get_recent_history(db)
    assert [row["turn_number"] for row in history] == [1, 1]
    assert history[0]["content"].index("First:") < history[0]["content"].index("Second:")
    assert len(run.calls) == 1
    assert game_master._batch_task is None
    await assert_connections_closed(run)


@pytest.mark.asyncio
async def test_enqueue_at_consumer_release_is_not_stranded(db, queue_run):
    run = queue_run
    await submit(run, "First: wait by the gate.")
    consumer = game_master._batch_task
    await asyncio.wait_for(run.started.wait(), timeout=5)
    lock = game_master._batch_lock
    await lock.acquire()
    try:
        run.release.set()
        await asyncio.wait_for(run.consumer_waiting.wait(), timeout=5)
        run.submitter_waiting.clear()
        enqueue = asyncio.create_task(submit(run, "Handoff: wait by the gate."))
        await asyncio.wait_for(run.submitter_waiting.wait(), timeout=5)
    finally:
        lock.release()
    await finish(enqueue)
    successor = game_master._batch_task
    assert successor is not None and successor is not consumer
    await finish(consumer)
    await finish(successor)

    history = await state_manager.get_recent_history(db)
    assert [row["turn_number"] for row in history] == [1, 1, 2, 2]
    assert "Handoff:" in history[2]["content"]
    assert [task for task, _ in run.calls] == [consumer, successor]
    assert game_master._pending_actions == []
    assert game_master._batch_task is None
    await assert_connections_closed(run)


@pytest.mark.asyncio
async def test_processing_exception_drains_late_work_without_replaying_partial_turn(db, queue_run, caplog):
    run = queue_run
    run.fail_summary = True
    await submit(run, "First: wait by the gate.")
    consumer = game_master._batch_task
    await asyncio.wait_for(run.started.wait(), timeout=5)
    await submit(run, "Late: wait by the gate.")
    run.release.set()
    await finish(consumer)

    history = await state_manager.get_recent_history(db)
    assert [row["turn_number"] for row in history] == [1, 1, 2, 2]
    assert "First:" in history[0]["content"]
    assert "Late:" in history[2]["content"]
    assert len(run.calls) == 2
    assert "Injected error transport failure" in caplog.text
    assert game_master._pending_actions == []
    assert game_master._batch_task is None
    await assert_connections_closed(run)


@pytest.mark.asyncio
@pytest.mark.parametrize("during_generation", [False, True])
async def test_cancellation_releases_resources_without_starting_consumer(db, queue_run, during_generation):
    run = queue_run
    if not during_generation:
        await submit(run, "First: wait by the gate.")
        await game_master._batch_lock.acquire()
        consumer = game_master._batch_task
        try:
            await asyncio.wait_for(run.initial_waiting.wait(), timeout=5)
            consumer.cancel()
        finally:
            game_master._batch_lock.release()
    else:
        await submit(run, "First: wait by the gate.")
        consumer = game_master._batch_task
        await asyncio.wait_for(run.started.wait(), timeout=5)
        await submit(run, "Late: wait by the gate.")
        consumer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await finish(consumer)

    assert consumer.cancelled()
    assert game_master._batch_task is None
    assert len(game_master._pending_actions) == 1
    assert not game_master.get_runtime_metrics()["batch_task_active"]
    assert len(run.calls) == int(during_generation)
    assert await state_manager.get_recent_history(db) == []
    await assert_connections_closed(run)
    owned_coroutines = {
        game_master._process_batch_after_window.__code__,
        game_master._thinking_timeout.__code__,
    }
    assert not any(
        task.get_coro().cr_code in owned_coroutines
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    )
