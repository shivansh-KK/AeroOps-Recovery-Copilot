"""Thread-safe SQLite access with transaction rollback and bounded connections."""
from contextlib import contextmanager
from pathlib import Path
from queue import LifoQueue, Empty
import sqlite3
from threading import Lock
from typing import Any, Iterator, Sequence


class DatabaseManager:
    def __init__(self, database_path: str | Path = "aero_ops.db", pool_size: int = 8) -> None:
        self.database_path = str(database_path)
        self._pool_size = max(1, pool_size)
        self._pool: LifoQueue[sqlite3.Connection] = LifoQueue(self._pool_size)
        self._created = 0
        self._creation_lock = Lock()
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Borrow a connection from the bounded pool and return it when finished."""
        try:
            connection = self._pool.get_nowait()
        except Empty:
            with self._creation_lock:
                if self._created < self._pool_size:
                    connection = sqlite3.connect(self.database_path, timeout=10, check_same_thread=False)
                    connection.row_factory = sqlite3.Row
                    connection.execute("PRAGMA foreign_keys = ON")
                    self._created += 1
                else:
                    connection = self._pool.get()
        try:
            yield connection
        finally:
            self._pool.put(connection)

    def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.executescript(schema)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as connection:
            try:
                connection.execute("BEGIN")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def query(self, sql: str, parameters: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, tuple(parameters)).fetchall()]

    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(sql, tuple(parameters))
            return int(cursor.rowcount)
