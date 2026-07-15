from __future__ import annotations

import csv
import json
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable

from .models import UploadItem, UploadResult
from .paths import AppPaths


MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version(version)
          SELECT 0 WHERE NOT EXISTS (SELECT 1 FROM schema_version);
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
        CREATE TABLE IF NOT EXISTS queue_snapshots (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          payload_json TEXT NOT NULL,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
]


class Database:
    def __init__(self, paths: AppPaths):
        self.path = paths.database
        self._lock = threading.RLock()
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, closing(self.connect()) as connection, connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
            row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                connection.execute("INSERT INTO schema_version(version) VALUES (0)")
                current = 0
            else:
                current = int(row[0])
            for version, sql in MIGRATIONS:
                if version > current:
                    connection.executescript(sql)
                    connection.execute("UPDATE schema_version SET version = ?", (version,))

    def add_upload(
        self,
        item: UploadItem,
        result: UploadResult,
        channel_id: str = "",
        channel_name: str = "",
    ) -> int:
        values = (
            item.id,
            item.filename,
            str(Path(item.source_path).resolve()).casefold(),
            item.file_size,
            item.modified_ns,
            item.file_hash,
            item.beat_name,
            item.collaborator,
            item.display_title,
            item.description,
            json.dumps(item.tags, ensure_ascii=False),
            channel_id,
            channel_name,
            result.youtube_id,
            result.youtube_url,
            result.started_at,
            result.completed_at,
            item.publish_at,
            result.status,
            item.preset_name,
            result.error,
        )
        with self._lock, closing(self.connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO uploads (
                  queue_item_id, original_filename, normalized_path, file_size, modified_ns,
                  sha256, beat_name, collaborator, title, description, tags_json, channel_id,
                  channel_name, youtube_id, youtube_url, upload_started, upload_completed,
                  publish_at, status, preset, error
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                values,
            )
            return int(cursor.lastrowid)

    def find_duplicates(self, item: UploadItem, channel_id: str = "") -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if item.file_hash:
            clauses.append("sha256 = ?")
            params.append(item.file_hash)
        clauses.append("(original_filename = ? AND file_size = ?)")
        params.extend([item.filename, item.file_size])
        if item.display_title:
            clauses.append("title = ?")
            params.append(item.display_title)
        channel_clause = " AND channel_id = ?" if channel_id else ""
        if channel_id:
            params.append(channel_id)
        query = f"SELECT * FROM uploads WHERE ({' OR '.join(clauses)}){channel_clause} ORDER BY id DESC"
        with self._lock, closing(self.connect()) as connection, connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def list_uploads(self, limit: int = 500, status: str = "") -> list[dict[str, Any]]:
        query = "SELECT * FROM uploads"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock, closing(self.connect()) as connection, connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def set_end_screen_done(self, upload_id: int, done: bool) -> None:
        with self._lock, closing(self.connect()) as connection, connection:
            connection.execute(
                "UPDATE uploads SET end_screen_done = ? WHERE id = ?", (int(done), upload_id)
            )

    def save_queue(self, items: Iterable[UploadItem]) -> None:
        payload = json.dumps([item.to_dict() for item in items], ensure_ascii=False)
        with self._lock, closing(self.connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO queue_snapshots(id, payload_json, updated_at) VALUES(1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET payload_json=excluded.payload_json,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (payload,),
            )

    def load_queue(self) -> list[UploadItem]:
        with self._lock, closing(self.connect()) as connection, connection:
            row = connection.execute("SELECT payload_json FROM queue_snapshots WHERE id=1").fetchone()
        if not row:
            return []
        try:
            return [UploadItem.from_dict(item) for item in json.loads(row[0])]
        except (json.JSONDecodeError, TypeError):
            return []

    def export_history_csv(self, path: Path) -> None:
        rows = self.list_uploads(limit=100000)
        fieldnames = [
            "created_at", "beat_name", "original_filename", "title", "collaborator",
            "preset", "channel_name", "status", "publish_at", "youtube_url", "error",
            "end_screen_done",
        ]
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
