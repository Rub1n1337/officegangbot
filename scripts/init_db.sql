-- OfficeGangBot PostgreSQL Schema
-- Run this script once to initialize all tables

-- Guild settings
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(10) DEFAULT '!',
    punishment_log_id BIGINT,
    usage_log_id BIGINT,
    leave_log_id BIGINT,
    audit_log_id BIGINT,
    welcome_channel_id BIGINT,
    welcome_message TEXT DEFAULT 'Welcome {user.mention} to **{server.name}**!',
    welcome_enabled BOOLEAN DEFAULT FALSE,
    autorole_id BIGINT,
    rules_channel_id BIGINT,
    rules_message_id BIGINT,
    rules_message TEXT,
    reaction_emoji VARCHAR(100),
    reaction_role_id BIGINT,
    setup_complete BOOLEAN DEFAULT FALSE,
    levels_enabled BOOLEAN DEFAULT TRUE,
    level_up_channel_id BIGINT,
    automod_enabled BOOLEAN DEFAULT TRUE,
    filter_enabled BOOLEAN DEFAULT FALSE,
    filter_words TEXT[] DEFAULT '{}',
    ticket_support_role_id BIGINT,
    ticket_category_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- XP and leveling system
CREATE TABLE IF NOT EXISTS users_xp (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    display_name VARCHAR(100),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (guild_id, user_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_xp_guild_xp ON users_xp(guild_id, xp DESC);

-- Warnings system
CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reason TEXT NOT NULL,
    moderator_id BIGINT NOT NULL,
    moderator_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_warnings_guild_user ON warnings(guild_id, user_id);

-- Timed punishments (temp mutes and bans)
CREATE TABLE IF NOT EXISTS timed_punishments (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    punishment_type VARCHAR(10) NOT NULL CHECK (punishment_type IN ('mute', 'ban')),
    reason TEXT,
    moderator_id BIGINT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (guild_id, user_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_timed_punishments_expires ON timed_punishments(expires_at);

-- Level role rewards
CREATE TABLE IF NOT EXISTS level_roles (
    guild_id BIGINT NOT NULL,
    level INTEGER NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, level),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Permission roles. role_type is a permission level ('config', 'kick', 'ban',
-- 'mute', 'warn', 'clear'). One role may hold several permission levels, so the
-- primary key includes role_type.
CREATE TABLE IF NOT EXISTS mod_roles (
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    role_type VARCHAR(20) NOT NULL,
    PRIMARY KEY (guild_id, role_id, role_type),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Reaction roles. Each row maps an emoji on a specific message to a role.
-- `source` distinguishes standalone reaction roles ('reaction-role') from the
-- one tied to the rules message ('rules'), so the cog can gate each by the
-- right feature flag.
CREATE TABLE IF NOT EXISTS reaction_roles (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    emoji VARCHAR(100) NOT NULL,
    role_id BIGINT NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'reaction-role',
    UNIQUE (guild_id, message_id, emoji),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reaction_roles_lookup ON reaction_roles(guild_id, message_id);

-- Audit trail of changes made through the web dashboard (moderation actions,
-- feature toggles, setting changes), so admins have a record of who did what.
CREATE TABLE IF NOT EXISTS dashboard_audit (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    actor_id BIGINT,
    actor_name VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    target VARCHAR(200),
    detail TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dashboard_audit_guild ON dashboard_audit(guild_id, created_at DESC);

-- Scheduled / recurring announcements configured from the dashboard. The bot's
-- Scheduled Messages cog polls this table and posts due messages.
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    repeat VARCHAR(10) NOT NULL DEFAULT 'none',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scheduled_messages_due ON scheduled_messages(scheduled_at) WHERE enabled;

-- Role menus: an embed the bot posts/edits in a channel, whose emoji reactions
-- grant roles. The emoji->role mappings live in reaction_roles (source='menu',
-- keyed by the posted message_id); this table tracks the menu's message so it
-- can be edited/deleted on later saves.
CREATE TABLE IF NOT EXISTS reaction_menus (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT,
    title VARCHAR(256) NOT NULL DEFAULT 'Role Menu',
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reaction_menus_guild ON reaction_menus(guild_id);

-- Tickets: one row per support ticket. Created when a member opens a ticket,
-- carries a priority while open, and is finalized on close with the closer, an
-- optional comment and a captured transcript of the channel's messages. Kept
-- after the channel is deleted so the dashboard can show closed-ticket history.
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    opener_id BIGINT NOT NULL,
    opener_name TEXT,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium',
    status VARCHAR(10) NOT NULL DEFAULT 'open',
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    closed_by_id BIGINT,
    closed_by_name TEXT,
    close_comment TEXT,
    transcript TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tickets_guild ON tickets(guild_id, status);
-- Hot lookup: get/close/set-priority all resolve the open ticket by channel id.
CREATE INDEX IF NOT EXISTS idx_tickets_channel ON tickets(channel_id);
-- At most one open ticket record per channel.
CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_open_channel ON tickets(channel_id) WHERE status = 'open';

-- Moderation cases: every moderation action gets a per-guild sequential case
-- number for reference (/case <n>). Allocation is serialized per guild with an
-- advisory lock in add_mod_case; the UNIQUE constraint is the backstop.
CREATE TABLE IF NOT EXISTS mod_cases (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    case_number INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_id BIGINT,
    target_name TEXT,
    moderator_id BIGINT,
    moderator_name TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (guild_id, case_number),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mod_cases_guild ON mod_cases(guild_id, case_number DESC);
CREATE INDEX IF NOT EXISTS idx_mod_cases_target ON mod_cases(guild_id, target_id);

-- Temporary roles: a role granted to a member until expires_at, then removed by
-- the timed_events expiry loop.
CREATE TABLE IF NOT EXISTS temp_roles (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    moderator_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (guild_id, user_id, role_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temp_roles_expiry ON temp_roles(expires_at);

-- AutoMod strikes: one row per recorded violation; the count within the guild's
-- decay window drives escalation.
CREATE TABLE IF NOT EXISTS automod_strikes (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_automod_strikes ON automod_strikes(guild_id, user_id, created_at);

-- AutoMod custom rules: per-guild regex patterns that delete a message (and
-- optionally add a strike) when they match.
CREATE TABLE IF NOT EXISTS automod_rules (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    pattern TEXT NOT NULL,
    action VARCHAR(10) NOT NULL DEFAULT 'delete',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_automod_rules_guild ON automod_rules(guild_id);

-- Levels: per-role XP multipliers. A member's effective multiplier is the
-- global guild multiplier times the highest role multiplier they hold.
CREATE TABLE IF NOT EXISTS level_multiplier_roles (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    multiplier NUMERIC(4,2) NOT NULL DEFAULT 1.0,
    UNIQUE (guild_id, role_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_level_multiplier_roles_guild ON level_multiplier_roles(guild_id);

-- Levels: archive of past seasons. /season_reset snapshots the standings here
-- and zeroes everyone's season XP (prestige is preserved).
CREATE TABLE IF NOT EXISTS level_seasons (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    season_number INTEGER NOT NULL,
    ended_at TIMESTAMPTZ DEFAULT NOW(),
    standings JSONB NOT NULL DEFAULT '[]',
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_level_seasons_guild ON level_seasons(guild_id, season_number DESC);

-- Activity analytics: an *aggregate* count of human messages per guild, bucketed
-- by weekday (0=Mon..6=Sun) and hour (0-23, UTC). Deliberately stores NO message
-- content, author or per-message timestamp — only a running count per bucket, so
-- there is nothing to age out and no PII. Powers the dashboard activity heatmap.
CREATE TABLE IF NOT EXISTS activity_buckets (
    guild_id BIGINT NOT NULL,
    weekday SMALLINT NOT NULL,
    hour SMALLINT NOT NULL,
    count BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, weekday, hour),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Ban appeals: a banned user's request to be unbanned, submitted from the ban
-- DM (button + modal). One active appeal per (guild, user); moderators review
-- and approve (unban) / deny from the dashboard.
CREATE TABLE IF NOT EXISTS ban_appeals (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    user_name VARCHAR(100),
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    decided_by_id BIGINT,
    decided_by_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    UNIQUE (guild_id, user_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ban_appeals_guild ON ban_appeals(guild_id, status, created_at DESC);

-- Migration: Add missing columns if they don't exist (for existing databases)
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS enabled_features TEXT[] DEFAULT '{}';
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS usage_log_id BIGINT;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS locale VARCHAR(5) DEFAULT 'en';
-- AutoMod content-filter config (invite/link blocking).
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_block_invites BOOLEAN DEFAULT FALSE;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_block_links BOOLEAN DEFAULT FALSE;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_allowed_domains TEXT[] DEFAULT '{}';
-- AutoMod anti-spam / mention thresholds (configurable from the dashboard).
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_spam_count INTEGER DEFAULT 5;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_spam_window INTEGER DEFAULT 3;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_mention_limit INTEGER DEFAULT 5;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_block_mass_mentions BOOLEAN DEFAULT FALSE;
-- AutoMod dry-run: detect + log violations without deleting/timing-out/striking,
-- so admins can tune filters safely before enforcing.
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_dry_run BOOLEAN DEFAULT FALSE;
-- AutoMod exemptions: channels and roles that bypass AutoMod entirely
-- (e.g. a #media channel or a trusted role).
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_ignored_channels BIGINT[] DEFAULT '{}';
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_ignored_roles BIGINT[] DEFAULT '{}';
-- Warning escalation: manual /warn auto-escalates (mute/kick/ban) once a member's
-- active warning count crosses the thresholds (0 = that tier off; expiry 0 = warns
-- never decay). Mirrors the AutoMod strike system for manual warnings.
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS warn_escalation_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS warn_expiry_hours INTEGER DEFAULT 0;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS warn_mute_at INTEGER DEFAULT 0;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS warn_kick_at INTEGER DEFAULT 0;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS warn_ban_at INTEGER DEFAULT 0;
-- Anti-raid: when the 'anti-raid' feature is enabled, a spike of joins
-- (join_count within join_window seconds) triggers raid mode for `duration`
-- seconds, applying `action` (timeout/kick/ban/notify) to the raiders.
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS antiraid_join_count INTEGER DEFAULT 8;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS antiraid_join_window INTEGER DEFAULT 10;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS antiraid_action VARCHAR(20) DEFAULT 'timeout';
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS antiraid_duration INTEGER DEFAULT 300;
-- AutoMod strike escalation: each violation records a strike; at the configured
-- thresholds the member is muted / kicked / banned (0 = that tier disabled).
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_strikes_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_strike_expiry_hours INTEGER DEFAULT 24;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_strike_mute_at INTEGER DEFAULT 3;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_strike_kick_at INTEGER DEFAULT 5;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS automod_strike_ban_at INTEGER DEFAULT 0;
-- Levels: voice XP, global multiplier, prestige threshold and season counter.
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS levels_voice_xp_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS levels_voice_xp_per_min INTEGER DEFAULT 5;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS levels_xp_multiplier NUMERIC(4,2) DEFAULT 1.0;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS levels_prestige_level INTEGER DEFAULT 100;
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS levels_season INTEGER DEFAULT 1;
-- Levels: lifetime prestige count per member (survives season/prestige resets).
ALTER TABLE users_xp ADD COLUMN IF NOT EXISTS prestige INTEGER DEFAULT 0;
-- Reaction menus: exclusive (single-select) mode — picking a role in the menu
-- removes the member's other roles from the same menu.
ALTER TABLE reaction_menus ADD COLUMN IF NOT EXISTS exclusive BOOLEAN DEFAULT FALSE;
-- Tickets: auto-close open tickets after this many hours of inactivity
-- (0 = disabled).
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS ticket_auto_close_hours INTEGER DEFAULT 0;
-- Ban appeals: when on, ban DMs include an "Appeal" button (opt-in per guild).
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS ban_appeals_enabled BOOLEAN DEFAULT FALSE;

-- Migration: relax mod_roles to store permission-level role_types and allow a
-- role to hold multiple permissions (older schema used CHECK ('mod','admin')
-- and PK (guild_id, role_id), which rejected /config role assignments).
DO $$
BEGIN
    ALTER TABLE mod_roles DROP CONSTRAINT IF EXISTS mod_roles_role_type_check;
    ALTER TABLE mod_roles ALTER COLUMN role_type TYPE VARCHAR(20);
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'mod_roles_pkey'
          AND conrelid = 'mod_roles'::regclass
          AND array_length(conkey, 1) = 2
    ) THEN
        ALTER TABLE mod_roles DROP CONSTRAINT mod_roles_pkey;
        ALTER TABLE mod_roles ADD PRIMARY KEY (guild_id, role_id, role_type);
    END IF;
END $$;

-- Security: enable RLS (deny-all, no policies) on all tables. The bot connects
-- directly as the postgres role and bypasses RLS, so its behavior is unchanged;
-- this closes the auto-exposed Supabase/PostgREST API to the anon key.
ALTER TABLE guilds ENABLE ROW LEVEL SECURITY;
ALTER TABLE users_xp ENABLE ROW LEVEL SECURITY;
ALTER TABLE warnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE timed_punishments ENABLE ROW LEVEL SECURITY;
ALTER TABLE level_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE mod_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE reaction_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE reaction_menus ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE mod_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE temp_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE automod_strikes ENABLE ROW LEVEL SECURITY;
ALTER TABLE automod_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE level_multiplier_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE level_seasons ENABLE ROW LEVEL SECURITY;
