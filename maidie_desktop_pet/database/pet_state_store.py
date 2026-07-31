from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Iterator

from core.pet_state import PetStateData


class PetStateStore:
    """SQLite persistence for the single local Maidie pet profile."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=3)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pet_state (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    mood INTEGER NOT NULL,
                    energy INTEGER NOT NULL,
                    affection INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    first_meet_time TEXT NOT NULL,
                    interaction_count INTEGER NOT NULL,
                    interaction_date TEXT NOT NULL,
                    chat_count INTEGER NOT NULL,
                    headpat_count INTEGER NOT NULL,
                    click_count INTEGER NOT NULL
                )
                """
            )

    def load(self) -> PetStateData:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM pet_state WHERE id = 1"
            ).fetchone()
        if row is None:
            state = PetStateData()
            self.save(state)
            return state
        try:
            first_meet_time = datetime.fromisoformat(str(row["first_meet_time"]))
        except (TypeError, ValueError):
            first_meet_time = datetime.now().astimezone()
        return PetStateData(
            mood=int(row["mood"]),
            energy=int(row["energy"]),
            affection=int(row["affection"]),
            level=int(row["level"]),
            first_meet_time=first_meet_time,
            interaction_count=int(row["interaction_count"]),
            interaction_date=str(row["interaction_date"]),
            chat_count=int(row["chat_count"]),
            headpat_count=int(row["headpat_count"]),
            click_count=int(row["click_count"]),
        )

    def save(self, state: PetStateData) -> None:
        first_meet_time = state.first_meet_time or datetime.now().astimezone()
        values = (
            int(state.mood),
            int(state.energy),
            int(state.affection),
            int(state.level),
            first_meet_time.isoformat(timespec="seconds"),
            int(state.interaction_count),
            str(state.interaction_date),
            int(state.chat_count),
            int(state.headpat_count),
            int(state.click_count),
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO pet_state (
                    id, mood, energy, affection, level, first_meet_time,
                    interaction_count, interaction_date, chat_count,
                    headpat_count, click_count
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    mood=excluded.mood,
                    energy=excluded.energy,
                    affection=excluded.affection,
                    level=excluded.level,
                    first_meet_time=excluded.first_meet_time,
                    interaction_count=excluded.interaction_count,
                    interaction_date=excluded.interaction_date,
                    chat_count=excluded.chat_count,
                    headpat_count=excluded.headpat_count,
                    click_count=excluded.click_count
                """,
                values,
            )
