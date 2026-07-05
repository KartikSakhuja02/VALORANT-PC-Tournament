-- =============================================================================
--  VALORANT PC Tournament — PostgreSQL Schema
--  Run this file with:
--    psql -U valorant_bot -d valorant_pc_tournament -h localhost -f schema.sql
-- =============================================================================

-- ── Custom Types ──────────────────────────────────────────────────────────────

CREATE TYPE registration_status AS ENUM (
    'pending',
    'approved',
    'rejected',
    'waitlisted',
    'disqualified'
);

CREATE TYPE region AS ENUM (
    'NA',       -- North America
    'EU',       -- Europe
    'AP',       -- Asia Pacific
    'KR',       -- Korea
    'LATAM',    -- Latin America
    'BR',       -- Brazil
    'ME'        -- Middle East
);

-- ── Teams ─────────────────────────────────────────────────────────────────────

CREATE TABLE teams (
    team_id             SERIAL          PRIMARY KEY,
    team_name           VARCHAR(64)     NOT NULL UNIQUE,
    captain_discord_id  VARCHAR(32)     NOT NULL UNIQUE,
    captain_email       VARCHAR(255)    NOT NULL UNIQUE,
    region              region          NOT NULL,
    logo_url            TEXT,
    discord_role_id     VARCHAR(32)     UNIQUE,
    registration_status registration_status NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ── Players ───────────────────────────────────────────────────────────────────

CREATE TABLE players (
    player_id       SERIAL          PRIMARY KEY,
    team_id         INTEGER         NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    discord_id      VARCHAR(32)     UNIQUE,                  -- NULL until they join the server
    email           VARCHAR(255)    NOT NULL UNIQUE,
    ign             VARCHAR(64)     NOT NULL,                -- In-Game Name (e.g. "Shroud#1234")
    region          region          NOT NULL,
    is_captain      BOOLEAN         NOT NULL DEFAULT FALSE,
    is_substitute   BOOLEAN         NOT NULL DEFAULT FALSE,
    joined_server   BOOLEAN         NOT NULL DEFAULT FALSE,
    verified        BOOLEAN         NOT NULL DEFAULT FALSE
);

-- At most one captain per team
CREATE UNIQUE INDEX one_captain_per_team
    ON players (team_id)
    WHERE is_captain = TRUE;

-- ── Invites ───────────────────────────────────────────────────────────────────

CREATE TABLE invites (
    invite_code         VARCHAR(64)     PRIMARY KEY,
    team_id             INTEGER         NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    player_email        VARCHAR(255)    NOT NULL,
    discord_invite_link TEXT,
    used                BOOLEAN         NOT NULL DEFAULT FALSE,
    used_by_discord_id  VARCHAR(32),                         -- NULL until claimed
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ── Tournament ────────────────────────────────────────────────────────────────
-- Single-row table — one active tournament at a time.
-- Enforced by the CHECK constraint on tournament_lock.

CREATE TABLE tournament (
    tournament_lock     BOOLEAN         PRIMARY KEY DEFAULT TRUE,   -- always TRUE, ensures 1 row
    tournament_name     VARCHAR(128)    NOT NULL,
    registration_open   TIMESTAMPTZ     NOT NULL,
    registration_close  TIMESTAMPTZ     NOT NULL,
    max_teams           SMALLINT        NOT NULL CHECK (max_teams > 0),
    current_teams       SMALLINT        NOT NULL DEFAULT 0 CHECK (current_teams >= 0),

    CONSTRAINT single_row CHECK (tournament_lock = TRUE),
    CONSTRAINT close_after_open CHECK (registration_close > registration_open),
    CONSTRAINT teams_within_limit CHECK (current_teams <= max_teams)
);

-- ── Auto-increment current_teams when a team is approved ─────────────────────

CREATE OR REPLACE FUNCTION sync_current_teams()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Increment when a team is newly approved
    IF NEW.registration_status = 'approved' AND
       (OLD.registration_status IS DISTINCT FROM 'approved') THEN
        UPDATE tournament SET current_teams = current_teams + 1;
    END IF;

    -- Decrement when a team loses approved status
    IF OLD.registration_status = 'approved' AND
       NEW.registration_status <> 'approved' THEN
        UPDATE tournament SET current_teams = GREATEST(current_teams - 1, 0);
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sync_current_teams
AFTER UPDATE ON teams
FOR EACH ROW EXECUTE FUNCTION sync_current_teams();

-- ── Indexes for common query patterns ─────────────────────────────────────────

CREATE INDEX idx_players_team_id      ON players (team_id);
CREATE INDEX idx_players_discord_id   ON players (discord_id);
CREATE INDEX idx_invites_team_id      ON invites (team_id);
CREATE INDEX idx_invites_player_email ON invites (player_email);
CREATE INDEX idx_teams_status         ON teams   (registration_status);

-- =============================================================================
--  Done. Verify with:
--    \dt          — list tables
--    \d teams     — inspect the teams table
-- =============================================================================
