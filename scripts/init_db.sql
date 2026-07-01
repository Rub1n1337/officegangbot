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
