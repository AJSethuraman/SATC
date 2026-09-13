-- pogo-forge schema
-- Phase 1: roster + particle planner.  Phase 2: filter library.
-- Phase 3 tables are defined but unused by the current UI.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- phase 1 --
CREATE TABLE IF NOT EXISTS pokemon (
  id          INTEGER PRIMARY KEY,
  species     TEXT    NOT NULL,
  nickname    TEXT,
  role        TEXT    NOT NULL DEFAULT 'attacker'
              CHECK (role IN ('attacker','defender','healer','bench')),
  max_form    TEXT    NOT NULL DEFAULT 'dynamax'
              CHECK (max_form IN ('dynamax','gigantamax','none')),
  fast_type   TEXT,                       -- sets Max Attack type on dynamax
  cp          INTEGER,
  iv_atk      INTEGER CHECK (iv_atk  BETWEEN 0 AND 15),
  iv_def      INTEGER CHECK (iv_def  BETWEEN 0 AND 15),
  iv_hp       INTEGER CHECK (iv_hp   BETWEEN 0 AND 15),
  priority    INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
  notes       TEXT,
  archived    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- One row per Max Move slot per Pokemon. level 0 = locked.
CREATE TABLE IF NOT EXISTS max_move (
  pokemon_id  INTEGER NOT NULL REFERENCES pokemon(id) ON DELETE CASCADE,
  slot        TEXT    NOT NULL CHECK (slot IN ('attack','guard','spirit')),
  level       INTEGER NOT NULL DEFAULT 0 CHECK (level BETWEEN 0 AND 3),
  PRIMARY KEY (pokemon_id, slot)
);

-- Append-only particle ledger. Balance is the running sum; nothing is edited.
CREATE TABLE IF NOT EXISTS particle_entry (
  id          INTEGER PRIMARY KEY,
  delta       INTEGER NOT NULL,           -- positive = earned, negative = spent
  reason      TEXT    NOT NULL,
  pokemon_id  INTEGER REFERENCES pokemon(id) ON DELETE SET NULL,
  slot        TEXT,
  at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Costs vary by species and are not published anywhere reliable.
-- Enter them as you meet them; the planner treats a missing cost as unknown.
CREATE TABLE IF NOT EXISTS move_cost (
  species     TEXT    NOT NULL,
  slot        TEXT    NOT NULL CHECK (slot IN ('attack','guard','spirit')),
  to_level    INTEGER NOT NULL CHECK (to_level BETWEEN 1 AND 3),
  particles   INTEGER NOT NULL,
  candy       INTEGER NOT NULL DEFAULT 0,
  candy_xl    INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (species, slot, to_level)
);

-- ---------------------------------------------------------------- phase 2 --
CREATE TABLE IF NOT EXISTS saved_filter (
  id          INTEGER PRIMARY KEY,
  name        TEXT    NOT NULL UNIQUE,
  query       TEXT    NOT NULL,
  note        TEXT,
  destructive INTEGER NOT NULL DEFAULT 0, -- 1 = used before a bulk transfer
  last_run    TEXT,
  created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------- phase 3 --
-- Full collection tracker. Defined now so migrations stay boring later.
CREATE TABLE IF NOT EXISTS collection_entry (
  id          INTEGER PRIMARY KEY,
  species     TEXT    NOT NULL,
  nickname    TEXT,
  cp          INTEGER,
  iv_atk      INTEGER,
  iv_def      INTEGER,
  iv_hp       INTEGER,
  gender      TEXT,
  shiny       INTEGER NOT NULL DEFAULT 0,
  lucky       INTEGER NOT NULL DEFAULT 0,
  shadow      INTEGER NOT NULL DEFAULT 0,
  caught_on   TEXT,
  caught_at   TEXT,
  tags        TEXT,
  verdict     TEXT CHECK (verdict IN ('keep','transfer','undecided')),
  source      TEXT NOT NULL DEFAULT 'manual',
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pokemon_active   ON pokemon(archived, priority);
CREATE INDEX IF NOT EXISTS idx_particle_at      ON particle_entry(at);
CREATE INDEX IF NOT EXISTS idx_collection_verdict ON collection_entry(verdict);
