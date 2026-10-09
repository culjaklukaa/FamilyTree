import sqlite3
from pathlib import Path
from typing import Optional

class Database:
    """Manages SQLite connection and simple migrations."""
    def __init__(self, db_path: Path | str = ":memory:"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def data_dir(self) -> Path:
        """Directory containing the database file.

        Media and thumbnails are stored in sub-folders here so a single
        folder copy backs up everything.  For in-memory databases (tests)
        this returns a 'data' directory relative to cwd.
        """
        if str(self.db_path) == ":memory:":
            return Path("data")
        return Path(self.db_path).parent

    @property
    def media_dir(self) -> Path:
        """Sub-directory for media files (alongside the DB)."""
        return self.data_dir / "media"

    @property
    def thumbnail_dir(self) -> Path:
        """Sub-directory for cached thumbnails."""
        return self.media_dir / "thumbnails"

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            # Enable foreign keys which are disabled by default in SQLite
            self._conn.execute("PRAGMA foreign_keys = ON;")
        return self._conn

    def close(self):
        """Closes the database connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def run_migrations(self, schema_dir: Path):
        """Applies SQL migration scripts from the given directory."""
        # Setup a migrations table if it doesn't exist
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY);"
        )
        self.connection.commit()

        cursor = self.connection.cursor()
        applied_versions = {
            row["version"] 
            for row in cursor.execute("SELECT version FROM schema_migrations").fetchall()
        }

        # Find and run new .sql files in order
        for sql_file in sorted(schema_dir.glob("*.sql")):
            version = sql_file.stem
            if version not in applied_versions:
                with open(sql_file, "r", encoding="utf-8") as f:
                    script = f.read()
                
                # Execute script
                cursor.executescript(script)
                # Record migration
                cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                self.connection.commit()

    def get_setting(self, key: str, default: str = None) -> str:
        """Retrieve a simple key-value setting."""
        # Ensure table exists (in case migrations haven't run or memory db not setup fully, though it should be)
        try:
            cursor = self.connection.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
        except sqlite3.OperationalError:
            pass
        return default

    def set_setting(self, key: str, value: str):
        """Save a simple key-value setting."""
        try:
            self.connection.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value)
            )
            self.connection.commit()
        except sqlite3.OperationalError:
            pass
