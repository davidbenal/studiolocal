-- StudioLocal — schema inicial v1
-- Aplicado uma vez por workspace ao rodar /studiolocal-install.

CREATE TABLE IF NOT EXISTS schema_version (
  version     INTEGER PRIMARY KEY,
  applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  slug         TEXT NOT NULL UNIQUE,
  name         TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'active',  -- active | archived
  tags         TEXT,                            -- JSON array
  budget_brl   REAL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  archived_at  TEXT
);

CREATE TABLE IF NOT EXISTS briefs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  path         TEXT NOT NULL,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id        INTEGER REFERENCES projects(id),
  opened_at         TEXT NOT NULL DEFAULT (datetime('now')),
  closed_at         TEXT,
  last_activity_at  TEXT NOT NULL DEFAULT (datetime('now')),
  notes             TEXT
);

CREATE TABLE IF NOT EXISTS workflows (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  slug               TEXT NOT NULL UNIQUE,
  name               TEXT NOT NULL,
  yaml_path          TEXT NOT NULL,
  created_at         TEXT NOT NULL DEFAULT (datetime('now')),
  source_session_id  INTEGER REFERENCES sessions(id),
  description        TEXT
);

CREATE TABLE IF NOT EXISTS runs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id  INTEGER NOT NULL REFERENCES workflows(id),
  project_id   INTEGER NOT NULL REFERENCES projects(id),
  session_id   INTEGER REFERENCES sessions(id),
  inputs       TEXT,
  status       TEXT NOT NULL DEFAULT 'running',  -- running | done | failed | paused
  started_at   TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at  TEXT,
  cost_brl     REAL DEFAULT 0,
  state        TEXT                              -- JSON com state da execução (p/ resume)
);

CREATE TABLE IF NOT EXISTS generations (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id      INTEGER NOT NULL REFERENCES projects(id),
  session_id      INTEGER NOT NULL REFERENCES sessions(id),
  run_id          INTEGER REFERENCES runs(id),
  step_index      INTEGER,
  model           TEXT NOT NULL,
  kind            TEXT NOT NULL,                  -- image | video | upscale
  prompt          TEXT,
  params          TEXT,
  status          TEXT NOT NULL DEFAULT 'pending',
  cost_brl        REAL DEFAULT 0,
  fal_request_id  TEXT,
  error           TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at     TEXT
);

CREATE TABLE IF NOT EXISTS assets (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  generation_id     INTEGER NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
  project_id        INTEGER NOT NULL REFERENCES projects(id),
  parent_asset_id   INTEGER REFERENCES assets(id),
  kind              TEXT NOT NULL,                -- image | video
  file_path         TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'draft', -- draft | library | discarded
  width             INTEGER,
  height            INTEGER,
  duration_s        REAL,
  bytes             INTEGER,
  promoted_at       TEXT,
  discarded_at      TEXT,
  created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO schema_version (version) VALUES (1);
