"""Campaign persistence checks with real disposable SQLite."""
import pytest
from src import state_manager as store, time_manager, travel_manager

async def seed(db):
    for pid, campaign in [('a', 'default'), ('a2', 'default'), ('b', 'other')]:
        await db.execute("INSERT INTO players (player_id, username, password_hash, name, campaign_id, created_at) VALUES (?, ?, 'hash', ?, ?, 123)", (pid, pid, pid, campaign))
        await store.upsert_character_memory(db, pid, 'memory-' + pid)
        await db.execute("INSERT INTO conditions VALUES (?, ?, 'poison', '', 3, 0, 0)", ('cond-' + pid, pid))
    await db.commit()

async def test_default_party_isolation(db):
    await seed(db)
    assert {p['player_id'] for p in await store.get_all_alive_players(db)} == {'a', 'a2'}

async def test_default_condition_isolation(db):
    await seed(db)
    await store.process_condition_turn(db, 1)
    assert (await store.get_player_by_id(db, 'b'))['current_hp'] == 100
    row = await (await db.execute("SELECT duration_turns FROM conditions WHERE player_id='b'")).fetchone()
    assert row[0] == 3

async def test_character_memory_membership(db):
    await seed(db)
    assert (await store.get_memory_layers(db, ['a', 'b'])).character == 'memory-a'

async def test_scoped_state_history_memory_calendar(db):
    await seed(db)
    for campaign, turn in [('default', 19), ('other', 3)]:
        await store.set_world_state(db, 'current_location', 'loc-' + campaign, campaign_id=campaign)
        await store.set_quest_flag(db, 'flag', campaign, campaign_id=campaign)
        await store.append_history(db, campaign, turn, 'user', campaign, campaign_id=campaign)
        await store.upsert_world_memory(db, 'world-' + campaign, campaign_id=campaign)
        await store.upsert_arc_memory(db, 'arc-' + campaign, campaign_id=campaign)
        assert await store.get_world_state(db, 'current_location', campaign_id=campaign) == 'loc-' + campaign
        assert await store.get_current_turn_number(db, campaign_id=campaign) == turn
        assert [r['content'] for r in await store.get_recent_history(db, 10, campaign_id=campaign)] == [campaign]
        assert await store.get_quest_flag(db, 'flag', campaign_id=campaign) == campaign
        layers = await store.get_memory_layers(db, ['a', 'b'], campaign_id=campaign)
        assert layers.world == 'world-' + campaign
        assert layers.arc == 'arc-' + campaign
        assert layers.character == ('memory-a' if campaign == 'default' else 'memory-b')
    await time_manager.advance_days(db, 40)
    await store.ensure_default_world_state(db, campaign_id='fresh')
    await time_manager.initialize_calendar(db, campaign_id='fresh')
    assert await store.get_world_state(db, 'current_location', campaign_id='fresh') == store.DEFAULT_START_LOCATION
    assert (await time_manager.get_current_date(db, campaign_id='fresh'))['day'] == 91
    await time_manager.advance_days(db, 2, campaign_id='other')
    assert (await time_manager.get_current_date(db))['day'] == 131
    await store.process_condition_turn(db, 1, campaign_id='other')
    assert (await store.get_player_by_id(db, 'a'))['current_hp'] == 100
    assert (await store.get_player_by_id(db, 'b'))['current_hp'] == 96

async def test_cooperative_and_travel_scope(db, monkeypatch):
    await seed(db)
    mission = await store.initialize_or_refresh_cooperative_mission(db)
    assert mission[store.COOP_MISSION_REQUIRED_PLAYERS_KEY] == '2'
    await store.initialize_or_refresh_cooperative_mission(db, campaign_id='other')
    with pytest.raises(ValueError):
        await store.mark_cooperative_mission_participation(db, 'b')
    await store.mark_cooperative_mission_participation(db, 'a')
    result = await store.mark_cooperative_mission_participation(db, 'a2')
    assert result[store.COOP_MISSION_COMPLETED_KEY] == '1'
    monkeypatch.setattr(travel_manager, 'calculate_travel_days', lambda *args: 2)
    monkeypatch.setattr(travel_manager, 'get_current_segment_terrain', lambda *args: 'road')
    monkeypatch.setattr(travel_manager, 'get_location', lambda *args: None)
    await travel_manager.start_travel(db, 'origin', 'destination', campaign_id='other')
    assert await travel_manager.get_travel_state(db) == {'active': False}
    assert (await travel_manager.advance_travel_day(db, campaign_id='other'))['day_current'] == 2
    await travel_manager.advance_travel_day(db, campaign_id='other')
    assert await store.get_world_state(db, 'current_location', campaign_id='other') == 'destination'
    assert await store.get_world_state(db, 'current_location') == store.DEFAULT_START_LOCATION

@pytest.mark.parametrize('helper', ['rumor', 'reputation'])
@pytest.mark.parametrize('player_id', ['b', 'deleted'])
async def test_player_helpers_reject_foreign_and_missing_membership(db, monkeypatch, helper, player_id):
    from src import rumor_manager, reputation_gates
    await seed(db)
    monkeypatch.setattr(rumor_manager, '_load_rumors', lambda: [{'rumor_id': 'r', 'tension_min': 0, 'variants': {'neutral': 'rumor'}}])
    monkeypatch.setattr(reputation_gates, '_load_gates', lambda: [{'gate_id': 'g', 'faction_id': 'f', 'direction': 'up', 'threshold': 10, 'unlock_type': 'quest', 'description': 'gate', 'gm_hint': 'hint'}])
    with pytest.raises(ValueError, match='campaign'):
        if helper == 'rumor':
            await rumor_manager.get_active_rumors_for_player(db, player_id, None, 5)
        else:
            await reputation_gates.check_reputation_gates(db, player_id, 'f', 20, 0)
    assert await (await db.execute('SELECT * FROM quest_flags')).fetchall() == []

async def test_rumor_and_reputation_flags_are_campaign_owned(db, monkeypatch):
    from src import rumor_manager, reputation_gates
    await seed(db)
    monkeypatch.setattr(rumor_manager, '_load_rumors', lambda: [{'rumor_id': 'r', 'tension_min': 0, 'variants': {'neutral': 'rumor'}}])
    monkeypatch.setattr(reputation_gates, '_load_gates', lambda: [{'gate_id': 'g', 'faction_id': 'f', 'direction': 'up', 'threshold': 10, 'unlock_type': 'quest', 'description': 'gate', 'gm_hint': 'hint'}])
    await store.set_quest_flag(db, 'rumor_heard:r:b', '1')
    await store.set_quest_flag(db, 'rep_gate:g:b', '1')
    assert await rumor_manager.get_active_rumors_for_player(db, 'b', None, 5, campaign_id='other') == ['rumor']
    assert len(await reputation_gates.check_reputation_gates(db, 'b', 'f', 20, 0, campaign_id='other')) == 1
    assert await rumor_manager.get_active_rumors_for_player(db, 'b', None, 5, campaign_id='other') == []
    assert await reputation_gates.check_reputation_gates(db, 'b', 'f', 20, 0, campaign_id='other') == []

async def test_fresh_defaults_are_idempotent_and_preserve_runtime(db):
    for campaign in ['default', 'other']:
        await store.ensure_default_world_state(db, campaign_id=campaign)
        await time_manager.initialize_calendar(db, campaign_id=campaign)
        await store.set_world_state(db, 'tension_level', '9', campaign_id=campaign)
        await store.set_world_state(db, 'campaign_paused', '1', campaign_id=campaign)
        await store.set_world_state(db, 'current_location', 'live-' + campaign, campaign_id=campaign)
        await time_manager.advance_days(db, 33, campaign_id=campaign)
    before = [tuple(r) for r in await (await db.execute('SELECT * FROM world_state ORDER BY campaign_id,key')).fetchall()]
    for campaign in ['default', 'other']:
        await store.ensure_default_world_state(db, campaign_id=campaign)
        await time_manager.initialize_calendar(db, campaign_id=campaign)
    assert [tuple(r) for r in await (await db.execute('SELECT * FROM world_state ORDER BY campaign_id,key')).fetchall()] == before
    await store.ensure_default_world_state(db, campaign_id='fresh')
    await time_manager.initialize_calendar(db, campaign_id='fresh')
    assert await store.get_world_state(db, 'tension_level', campaign_id='fresh') == '5'
    assert await store.get_world_state(db, 'campaign_paused', campaign_id='fresh') == '0'
    assert await store.get_world_state(db, 'current_location', campaign_id='fresh') == store.DEFAULT_START_LOCATION
    assert (await time_manager.get_current_date(db, campaign_id='fresh'))['day'] == 91
    assert await store.get_recent_history(db, campaign_id='fresh') == []
    assert await store.get_cooperative_mission_state(db, campaign_id='fresh') == {}
    layers = await store.get_memory_layers(db, [], campaign_id='fresh')
    assert layers.world == layers.arc == layers.character == ''
