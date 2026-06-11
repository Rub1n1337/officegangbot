# scripts/migrate_json_to_pg.py
"""
One-time migration script: reads guild_settings.json and writes all data to PostgreSQL.
Run once after setting up the database:
    python scripts/migrate_json_to_pg.py
"""

import asyncio
import asyncpg
import json
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'guild_settings.json')
DATABASE_URL = os.getenv("DATABASE_URL")


async def migrate():
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set in .env")
        return

    if not os.path.exists(DATA_PATH):
        print(f"❌ guild_settings.json not found at {DATA_PATH}")
        return

    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=3)
    print(f"✅ Connected to PostgreSQL. Migrating {len(data)} guilds...")

    guild_count = 0
    warning_count = 0
    xp_count = 0
    punishment_count = 0

    async with pool.acquire() as conn:
        for guild_id_str, settings in data.items():
            guild_id = int(guild_id_str)

            # --- Migrate guild settings ---
            await conn.execute("""
                INSERT INTO guilds (
                    guild_id, prefix, punishment_log_id, usage_log_id,
                    leave_log_id, audit_log_id, welcome_channel_id,
                    welcome_message, welcome_enabled, autorole_id,
                    rules_channel_id, rules_message_id, rules_message,
                    reaction_emoji, reaction_role_id, setup_complete,
                    levels_enabled, level_up_channel_id, automod_enabled,
                    filter_enabled, ticket_support_role_id, ticket_category_id
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22
                )
                ON CONFLICT (guild_id) DO UPDATE SET
                    prefix = EXCLUDED.prefix,
                    punishment_log_id = EXCLUDED.punishment_log_id,
                    updated_at = NOW()
            """,
                guild_id,
                settings.get('prefix', '!'),
                _to_int(settings.get('punishment_log_id')),
                _to_int(settings.get('usage_log_id')),
                _to_int(settings.get('leave_log_id')),
                _to_int(settings.get('audit_log_id')),
                _to_int(settings.get('welcome_channel_id')),
                settings.get('welcome_message', 'Welcome {user.mention} to **{server.name}**!'),
                bool(settings.get('welcome_enabled', False)),
                _to_int(settings.get('autorole_id')),
                _to_int(settings.get('rules_channel_id')),
                _to_int(settings.get('rules_message_id')),
                settings.get('rules_message'),
                settings.get('reaction_emoji'),
                _to_int(settings.get('reaction_role_id')),
                bool(settings.get('setup_complete', False)),
                bool(settings.get('levels_enabled', True)),
                _to_int(settings.get('level_up_channel_id')),
                bool(settings.get('automod_enabled', True)),
                bool(settings.get('filter_enabled', False)),
                _to_int(settings.get('ticket_support_role_id')),
                _to_int(settings.get('ticket_category_id')),
            )
            guild_count += 1

            # --- Migrate warnings ---
            warnings = settings.get('warnings', {})
            for user_id_str, user_warnings in warnings.items():
                user_id = int(user_id_str)
                for w in user_warnings:
                    await conn.execute("""
                        INSERT INTO warnings (guild_id, user_id, reason, moderator_id, moderator_name, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                        guild_id, user_id,
                        w.get('reason', 'No reason'),
                        int(w.get('moderator_id', 0)),
                        w.get('moderator_name', 'Unknown'),
                        _parse_datetime(w.get('timestamp'))
                    )
                    warning_count += 1

            # --- Migrate XP levels ---
            levels = settings.get('levels', {})
            for user_id_str, user_data in levels.items():
                user_id = int(user_id_str)
                await conn.execute("""
                    INSERT INTO users_xp (guild_id, user_id, xp, level, display_name)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (guild_id, user_id) DO UPDATE
                    SET xp = EXCLUDED.xp, level = EXCLUDED.level, display_name = EXCLUDED.display_name
                """,
                    guild_id, user_id,
                    int(user_data.get('xp', 0)),
                    int(user_data.get('level', 0)),
                    user_data.get('display_name')
                )
                xp_count += 1

            # --- Migrate timed punishments ---
            timed = settings.get('timed_punishments', {})
            for user_id_str, punishment in timed.items():
                user_id = int(user_id_str)
                expires_at = datetime.datetime.fromtimestamp(
                    punishment.get('expires_at', 0),
                    tz=datetime.timezone.utc
                )
                if expires_at > datetime.datetime.now(tz=datetime.timezone.utc):
                    await conn.execute("""
                        INSERT INTO timed_punishments (guild_id, user_id, punishment_type, expires_at, reason, moderator_id)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (guild_id, user_id) DO NOTHING
                    """,
                        guild_id, user_id,
                        punishment.get('type', 'mute'),
                        expires_at,
                        punishment.get('reason'),
                        int(punishment.get('moderator_id', 0)) or None
                    )
                    punishment_count += 1

            # --- Migrate level roles ---
            level_roles = settings.get('level_roles', {})
            for level_str, role_id_str in level_roles.items():
                await conn.execute("""
                    INSERT INTO level_roles (guild_id, level, role_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id, level) DO UPDATE SET role_id = EXCLUDED.role_id
                """,
                    guild_id, int(level_str), int(role_id_str)
                )

    await pool.close()

    print(f"""
✅ Migration complete!
   Guilds migrated:      {guild_count}
   Warnings migrated:    {warning_count}
   XP records migrated:  {xp_count}
   Timed punishments:    {punishment_count}
""")


def _to_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _parse_datetime(value: str) -> datetime.datetime:
    try:
        dt = datetime.datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return datetime.datetime.now(tz=datetime.timezone.utc)


if __name__ == "__main__":
    asyncio.run(migrate())
