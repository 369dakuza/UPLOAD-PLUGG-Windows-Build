CREATE TABLE IF NOT EXISTS uploads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  queue_item_id TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  normalized_path TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  modified_ns INTEGER NOT NULL,
  sha256 TEXT NOT NULL DEFAULT '',
  beat_name TEXT NOT NULL,
  collaborator TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  tags_json TEXT NOT NULL DEFAULT '[]',
  channel_id TEXT NOT NULL DEFAULT '',
  channel_name TEXT NOT NULL DEFAULT '',
  youtube_id TEXT NOT NULL DEFAULT '',
  youtube_url TEXT NOT NULL DEFAULT '',
  upload_started TEXT NOT NULL DEFAULT '',
  upload_completed TEXT NOT NULL DEFAULT '',
  publish_at TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  preset TEXT NOT NULL DEFAULT '',
  error TEXT NOT NULL DEFAULT '',
  end_screen_done INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_uploads_sha256 ON uploads(sha256);
CREATE INDEX IF NOT EXISTS idx_uploads_title ON uploads(title);
CREATE INDEX IF NOT EXISTS idx_uploads_path ON uploads(normalized_path);

