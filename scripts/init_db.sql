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

-- Moderation roles (mod/admin)
CREATE TABLE IF NOT EXISTS mod_roles (
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    role_type VARCHAR(10) NOT NULL CHECK (role_type IN ('mod', 'admin')),
    PRIMARY KEY (guild_id, role_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Migration: Add missing columns if they don't exist (for existing databases)
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS enabled_features TEXT[] DEFAULT '{}';
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS usage_log_id BIGINT;
