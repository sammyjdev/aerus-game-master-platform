"""Campaign migration preservation and injected upgrade rollback."""
import aiosqlite
import pytest
from src import migration_runner as runner

async def snapshot(conn):
    schema = await (await conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type,name")).fetchall()
    tables = [row[1] for row in schema if row[0] == 'table']
    data = {table: await (await conn.execute(f'SELECT * FROM "{table}" ORDER BY 1')).fetchall() for table in tables}
    return schema, data

async def test_runner_rolls_back_actual_mid_upgrade_failure(tmp_path, monkeypatch):
    async with aiosqlite.connect(tmp_path / 'atomic.db') as conn:
        await runner.run_migrations(conn)
        before = await snapshot(conn)
        migrations = tmp_path / 'injected'
        migrations.mkdir()
        path = migrations / '099_injected.sql'
        path.write_text("ALTER TABLE world_state ADD COLUMN atomic_probe TEXT; CREATE TABLE probe_copy AS SELECT * FROM world_state; INSERT INTO nonexistent VALUES (1);")
        monkeypatch.setattr(runner, 'MIGRATIONS_DIR', migrations)
        with pytest.raises(aiosqlite.OperationalError, match='nonexistent'):
            await runner.run_migrations(conn)
        assert await snapshot(conn) == before
        path.write_text("ALTER TABLE world_state ADD COLUMN atomic_probe TEXT; CREATE TABLE probe_copy AS SELECT * FROM world_state;")
        await runner.run_migrations(conn)
        after = await snapshot(conn)
        await runner.run_migrations(conn)
        assert await snapshot(conn) == after
    async with aiosqlite.connect(tmp_path / 'atomic.db') as conn:
        await runner.run_migrations(conn)
        assert await snapshot(conn) == after

@pytest.mark.parametrize('state', ['empty', 'through014', 'historical013', 'legacy'])
async def test_upgrade_preserves_all_data_and_history(tmp_path, monkeypatch, state):
    actual = runner.MIGRATIONS_DIR
    old_dir = tmp_path / 'old'
    old_dir.mkdir()
    for version, path in runner._discover_migrations():
        if version <= (12 if state == 'historical013' else 14):
            sql = path.read_text()
            if state == 'historical013' and version == 1:
                sql = '\n'.join(line for line in sql.splitlines() if not line.strip().startswith('magic_level '))
            (old_dir / path.name).write_text(sql)
    async with aiosqlite.connect(tmp_path / 'upgrade.db') as conn:
        old = None
        if state != 'empty':
            monkeypatch.setattr(runner, 'MIGRATIONS_DIR', old_dir)
            await runner.run_migrations(conn)
            monkeypatch.setattr(runner, 'MIGRATIONS_DIR', actual)
            if state == 'historical013':
                await conn.execute("ALTER TABLE players ADD COLUMN campaign_id TEXT NOT NULL DEFAULT 'default'")
                await conn.execute("INSERT INTO schema_migrations VALUES (13, '013_player_campaign.sql', 1234.5)")
            if state == 'legacy':
                await conn.execute('DROP TABLE schema_migrations')
            await conn.execute("INSERT INTO players (player_id, username, password_hash, campaign_id, created_at) VALUES ('p','user','hash','other',1.5)")
            await conn.execute("INSERT INTO inventory (item_id,player_id,name) VALUES ('i','p','sword')")
            await conn.execute("INSERT INTO history VALUES ('h',27,'user','old-history',12.25)")
            await conn.execute("INSERT INTO world_memory VALUES (42,'old-world',13.25)")
            await conn.execute("INSERT INTO arc_memory VALUES (72,'old-arc',14.25)")
            await conn.execute("INSERT INTO world_state VALUES ('calendar_day','200',15.25)")
            await conn.execute("INSERT INTO quest_flags VALUES ('rumor_heard:r:p','1',16.25)")
            await conn.execute("INSERT INTO invites VALUES ('invite','admin',1,'p',17.25)")
            await conn.execute("INSERT INTO sessions VALUES ('session','p','token',9999.25,18.25)")
            await conn.execute("INSERT INTO conditions VALUES ('condition','p','poison','legacy condition',5,27,0)")
            await conn.execute("INSERT INTO character_memory VALUES ('p','old-character',19.25)")
            await conn.execute("INSERT INTO player_episodes VALUES ('episode','p',27,'social_action','old episode',3,20.25)")
            await conn.execute("INSERT INTO faction_reputation VALUES ('p','guild_of_threads',45,21.25)")
            await conn.execute("INSERT INTO generated_images VALUES ('image','prompt','https://example.test/image','completed',22.25)")
            await conn.execute("INSERT INTO dice_roll_arguments (roll_id,player_id,roll_type,dc,description,initial_roll,initial_result,argument,argument_submitted,verdict,circumstance_bonus,final_result,explanation,created_at,resolved_at) VALUES ('roll','p','skill',12,'old roll',13,15,'argument',1,'accept_with_bonus',2,17,'explanation',23.25,24.25)")
            await conn.execute("INSERT INTO world_state VALUES ('current_location','custom-location',25.25)")
            await conn.execute("INSERT INTO quest_flags VALUES ('custom','legacy-value',26.25)")
            await conn.commit()
            old = (await snapshot(conn))[1]
        await runner.run_migrations(conn)
        for table in ['history','world_memory','arc_memory','world_state','quest_flags']:
            columns = await (await conn.execute(f'PRAGMA table_info({table})')).fetchall()
            assert 'campaign_id' in {r[1] for r in columns}
        if old:
            for table, rows in old.items():
                if table == 'schema_migrations':
                    continue
                columns = [r[1] for r in await (await conn.execute(f'PRAGMA table_info({table})')).fetchall()]
                new = await (await conn.execute(f'SELECT * FROM "{table}" ORDER BY 1')).fetchall()
                if table in ['history','world_memory','arc_memory','world_state','quest_flags']:
                    assert [tuple(value for i,value in enumerate(r) if columns[i] != 'campaign_id') for r in new] == rows
                    assert all(r[columns.index('campaign_id')] == 'default' for r in new)
                elif table == 'players' and state == 'historical013':
                    assert [r[:-1] for r in new] == rows
                else:
                    assert new == rows
            for record in old.get('schema_migrations', []):
                assert await (await conn.execute('SELECT * FROM schema_migrations WHERE version=?', (record[0],))).fetchone() == record
        before = await snapshot(conn)
        await runner.run_migrations(conn)
        assert await snapshot(conn) == before

@pytest.mark.parametrize('reopen', [False, True])
@pytest.mark.parametrize('after_sql', ['DROP TABLE world_state;', 'DROP TABLE quest_flags;'])
async def test_real_015_mid_replacement_rollback_and_retry(tmp_path, monkeypatch, reopen, after_sql):
    actual_dir = runner.MIGRATIONS_DIR
    old_dir = tmp_path / 'before015'
    old_dir.mkdir()
    for version, path in runner._discover_migrations():
        if version <= 14:
            (old_dir / path.name).write_text(path.read_text())
    monkeypatch.setattr(runner, 'MIGRATIONS_DIR', old_dir)
    database = tmp_path / 'real015.db'
    conn = await aiosqlite.connect(database)
    try:
        await runner.run_migrations(conn)
        await conn.execute("INSERT INTO world_state VALUES ('calendar_day','200',12.25)")
        await conn.execute("INSERT INTO quest_flags VALUES ('player:p','legacy',13.25)")
        await conn.execute("INSERT INTO history VALUES ('h',7,'user','history',14.25)")
        await conn.execute("INSERT INTO world_memory VALUES (45,'world',15.25)")
        await conn.execute("INSERT INTO arc_memory VALUES (76,'arc',16.25)")
        await conn.commit()
        before = await snapshot(conn)
        sql = (actual_dir / '015_campaign_persistence.sql').read_text()
        injected_dir = tmp_path / 'injected015'
        injected_dir.mkdir()
        injected_path = injected_dir / '015_campaign_persistence.sql'
        injected_path.write_text(sql.replace(after_sql, after_sql + '\nINSERT INTO nonexistent VALUES (1);'))
        monkeypatch.setattr(runner, 'MIGRATIONS_DIR', injected_dir)
        with pytest.raises(aiosqlite.OperationalError, match='nonexistent'):
            await runner.run_migrations(conn)
        assert not conn.in_transaction
        assert await snapshot(conn) == before
        if reopen:
            await conn.close()
            conn = await aiosqlite.connect(database)
            assert await snapshot(conn) == before
        injected_path.write_text(sql)
        await runner.run_migrations(conn)
        after = await snapshot(conn)
        await runner.run_migrations(conn)
        assert await snapshot(conn) == after
        assert await (await conn.execute('SELECT key,value,updated_at,campaign_id FROM world_state')).fetchall() == [('calendar_day','200',12.25,'default')]
        assert await (await conn.execute('SELECT flag_key,flag_value,updated_at,campaign_id FROM quest_flags')).fetchall() == [('player:p','legacy',13.25,'default')]
        for table in ['history', 'world_memory', 'arc_memory']:
            assert [row[:-1] for row in after[1][table]] == before[1][table]
    finally:
        await conn.close()
    async with aiosqlite.connect(database) as conn:
        assert await snapshot(conn) == after
        await runner.run_migrations(conn)
        assert await snapshot(conn) == after

async def test_campaign_keys_and_read_indexes(tmp_path):
    async with aiosqlite.connect(tmp_path / 'keys.db') as conn:
        await runner.run_migrations(conn)
        for table, key in [('world_state', 'key'), ('quest_flags', 'flag_key')]:
            columns = await (await conn.execute(f'PRAGMA table_info({table})')).fetchall()
            assert [row[1] for row in sorted(columns, key=lambda row: row[5]) if row[5]] == ['campaign_id', key]
        for index, expected in [
            ('idx_history_campaign_turn', ['campaign_id', 'turn_number', 'created_at']),
            ('idx_world_memory_campaign_time', ['campaign_id', 'updated_at']),
            ('idx_arc_memory_campaign_time', ['campaign_id', 'updated_at']),
        ]:
            info = await (await conn.execute(f'PRAGMA index_info({index})')).fetchall()
            assert [row[2] for row in info] == expected


async def test_upgrade_preserves_legacy_null_keys_and_flags(tmp_path, monkeypatch):
    actual = runner.MIGRATIONS_DIR
    old_dir = tmp_path / 'old_null'
    old_dir.mkdir()
    for version, path in runner._discover_migrations():
        if version <= 14:
            (old_dir / path.name).write_text(path.read_text())
    database = tmp_path / 'null_upgrade.db'
    async with aiosqlite.connect(database) as conn:
        monkeypatch.setattr(runner, 'MIGRATIONS_DIR', old_dir)
        await runner.run_migrations(conn)
        await conn.execute("INSERT INTO world_state (key, value, updated_at) VALUES (NULL, 'legacy_null_state', 10.5)")
        await conn.execute("INSERT INTO quest_flags (flag_key, flag_value, updated_at) VALUES (NULL, 'legacy_null_flag', 11.5)")
        await conn.commit()
        monkeypatch.setattr(runner, 'MIGRATIONS_DIR', actual)
        await runner.run_migrations(conn)
        rows_ws = await (await conn.execute("SELECT key, value, updated_at, campaign_id FROM world_state")).fetchall()
        assert rows_ws == [(None, 'legacy_null_state', 10.5, 'default')]
        rows_qf = await (await conn.execute("SELECT flag_key, flag_value, updated_at, campaign_id FROM quest_flags")).fetchall()
        assert rows_qf == [(None, 'legacy_null_flag', 11.5, 'default')]
