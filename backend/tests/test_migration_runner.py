"""Real SQL upgrade paths, data preservation, and migration idempotence."""
import aiosqlite
import pytest

from src import migration_runner


def test_discovered_versions_are_unique():
    versions = [version for version, _ in migration_runner._discover_migrations()]
    assert len(versions) == len(set(versions))


async def _snapshot(conn):
    schema = await (await conn.execute(
        "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
    )).fetchall()
    tables = ["players", "inventory", "history", "schema_migrations"]
    data = {}
    for table in tables:
        data[table] = await (await conn.execute(
            f"SELECT * FROM {table} ORDER BY 1"
        )).fetchall()
    return schema, data


@pytest.mark.parametrize("state,recorded_filename", [
    ("empty", None),
    ("legacy", None),
    ("through_012", None),
    ("magic", "013_magic_level.sql"),
    ("campaign", "013_player_campaign.sql"),
    ("both", "013_magic_level.sql"),
    ("both", "013_player_campaign.sql"),
])
async def test_upgrade_preserves_data_and_is_idempotent(
    tmp_path, monkeypatch, state, recorded_filename
):
    actual_dir = migration_runner.MIGRATIONS_DIR
    async with aiosqlite.connect(tmp_path / "upgrade.db") as conn:
        original_player = None
        original_inventory = None
        original_history = None
        if state != "empty":
            # Build a genuine pre-magic schema, unlike the current 001 baseline.
            old_dir = tmp_path / "through_012"
            old_dir.mkdir()
            for version, path in migration_runner._discover_migrations():
                if version <= 12:
                    sql = path.read_text(encoding="utf-8")
                    if version == 1:
                        sql = "\n".join(
                            line for line in sql.splitlines()
                            if not line.strip().startswith("magic_level ")
                        )
                    (old_dir / path.name).write_text(sql, encoding="utf-8")
            monkeypatch.setattr(migration_runner, "MIGRATIONS_DIR", old_dir)
            await migration_runner.run_migrations(conn)
            monkeypatch.setattr(migration_runner, "MIGRATIONS_DIR", actual_dir)
            columns = await (await conn.execute("PRAGMA table_info(players)")).fetchall()
            assert "magic_level" not in {row[1] for row in columns}
            if state in {"magic", "both"}:
                await conn.executescript((actual_dir / "013_magic_level.sql").read_text())
            if state in {"campaign", "both"}:
                await conn.execute(
                    "ALTER TABLE players ADD COLUMN campaign_id TEXT NOT NULL DEFAULT 'default'"
                )
                await conn.execute(
                    "CREATE INDEX idx_players_campaign ON players(campaign_id)"
                )
            if recorded_filename:
                await conn.execute(
                    "INSERT INTO schema_migrations VALUES (13, ?, 1234.5)",
                    (recorded_filename,),
                )
            if state == "legacy":
                await conn.execute("DROP TABLE schema_migrations")
            await conn.execute(
                "INSERT INTO players (player_id, username, password_hash, created_at) "
                "VALUES ('preserved', 'existing-user', 'existing-hash', 123.0)"
            )
            if state in {"magic", "both"}:
                await conn.execute("UPDATE players SET magic_level = 37")
            if state in {"campaign", "both"}:
                await conn.execute("UPDATE players SET campaign_id = 'custom-campaign'")
            await conn.execute(
                "INSERT INTO inventory (item_id, player_id, name, quantity) "
                "VALUES ('item', 'preserved', 'Existing sword', 3)"
            )
            await conn.execute(
                "INSERT INTO history VALUES ('turn', 7, 'user', 'Existing history', 456.0)"
            )
            conn.row_factory = aiosqlite.Row
            original_player = dict(await (await conn.execute("SELECT * FROM players")).fetchone())
            conn.row_factory = None
            original_inventory = await (await conn.execute("SELECT * FROM inventory")).fetchall()
            original_history = await (await conn.execute("SELECT * FROM history")).fetchall()
            await conn.commit()

        await migration_runner.run_migrations(conn)
        columns = {row[1]: row for row in await (
            await conn.execute("PRAGMA table_info(players)")
        ).fetchall()}
        assert columns["magic_level"][3:5] == (1, "0")
        assert columns["campaign_id"][3:5] == (1, "'default'")
        indexes = await (await conn.execute("PRAGMA index_info(idx_players_campaign)")).fetchall()
        assert [row[2] for row in indexes] == ["campaign_id"]
        if original_player is not None:
            conn.row_factory = aiosqlite.Row
            player = dict(await (await conn.execute("SELECT * FROM players")).fetchone())
            conn.row_factory = None
            assert {key: player[key] for key in original_player} == original_player
            assert player["magic_level"] == original_player.get("magic_level", 0)
            assert player["campaign_id"] == original_player.get("campaign_id", "default")
            assert await (await conn.execute("SELECT * FROM inventory")).fetchall() == original_inventory
            assert await (await conn.execute("SELECT * FROM history")).fetchall() == original_history
        if recorded_filename:
            assert await (await conn.execute(
                "SELECT filename, applied_at FROM schema_migrations WHERE version = 13"
            )).fetchone() == (recorded_filename, 1234.5)
        await conn.execute(
            "INSERT INTO players (player_id, username, password_hash, created_at) "
            "VALUES ('new', 'new-user', 'new-hash', 789.0)"
        )
        assert await (await conn.execute(
            "SELECT magic_level, campaign_id FROM players WHERE player_id = 'new'"
        )).fetchone() == (0, "default")
        await conn.commit()
        first_run = await _snapshot(conn)
        await migration_runner.run_migrations(conn)
        assert await _snapshot(conn) == first_run
