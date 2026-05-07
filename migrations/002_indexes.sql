-- StudioLocal — indexes para queries de report

CREATE INDEX IF NOT EXISTS idx_gen_project_date  ON generations(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_gen_model         ON generations(model);
CREATE INDEX IF NOT EXISTS idx_gen_session       ON generations(session_id);
CREATE INDEX IF NOT EXISTS idx_gen_run           ON generations(run_id);
CREATE INDEX IF NOT EXISTS idx_assets_status     ON assets(status, project_id);
CREATE INDEX IF NOT EXISTS idx_assets_parent     ON assets(parent_asset_id);
CREATE INDEX IF NOT EXISTS idx_assets_gen        ON assets(generation_id);
CREATE INDEX IF NOT EXISTS idx_runs_workflow     ON runs(workflow_id, started_at);
CREATE INDEX IF NOT EXISTS idx_runs_project      ON runs(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_open     ON sessions(closed_at) WHERE closed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_project  ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_projects_status   ON projects(status);

INSERT INTO schema_version (version) VALUES (2);
