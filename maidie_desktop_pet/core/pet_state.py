from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class PetStateData:
    """Persistent state for Maidie's lightweight companionship layer."""

    mood: int = 65
    energy: int = 82
    affection: int = 0
    level: int = 1
    first_meet_time: datetime | None = None
    interaction_count: int = 0
    interaction_date: str = ""
    chat_count: int = 0
    headpat_count: int = 0
    click_count: int = 0

    def __post_init__(self) -> None:
        if self.first_meet_time is None:
            object.__setattr__(self, "first_meet_time", datetime.now().astimezone())
        if not self.interaction_date:
            object.__setattr__(self, "interaction_date", date.today().isoformat())


class PetStateManager:
    """Own pet-state mutations and expose a UI-ready snapshot."""

    def __init__(self, store: Any | None = None) -> None:
        from core.affection_system import AffectionSystem
        from core.emotion_engine import EmotionEngine
        from core.time_manager import TimeManager

        self.store = store
        self.affection = AffectionSystem()
        self.emotion = EmotionEngine()
        self.time = TimeManager()
        self.state = self._load()

    def _load(self) -> PetStateData:
        if self.store is None:
            return PetStateData()
        try:
            return self.store.load()
        except Exception:
            return PetStateData()

    def record_interaction(self, interaction: str) -> dict[str, Any]:
        state = self._reset_daily_counts(self.state)
        state = self.affection.apply_interaction(state, interaction)
        counter_name = {
            "chat": "chat_count",
            "headpat": "headpat_count",
            "click": "click_count",
        }.get(interaction)
        changes: dict[str, Any] = {
            "mood": self.emotion.apply_interaction(state.mood, interaction),
        }
        if counter_name:
            changes[counter_name] = getattr(state, counter_name) + 1
        self.state = replace(state, **changes)
        self._save()
        return self.snapshot()

    def snapshot(self, emotion: str = "idle") -> dict[str, Any]:
        self.state = self._reset_daily_counts(self.state)
        first_meet_time = self.state.first_meet_time or datetime.now().astimezone()
        result = asdict(self.state)
        result.update(
            {
                "name": "Maidie",
                "relationship": self.affection.relationship_for(self.state.affection),
                "mood_label": self.emotion.display_mood(
                    emotion, energy=self.state.energy
                ),
                "companion_time": self.time.companion_time_text(first_meet_time),
            }
        )
        return result

    def set_mood(self, value: int) -> None:
        """Reserved entry point for a future emotion-to-state synchronizer."""
        self.state = replace(self.state, mood=max(0, min(100, int(value))))
        self._save()

    def set_energy(self, value: int) -> None:
        """Reserved entry point for future sleep/activity energy rules."""
        self.state = replace(self.state, energy=max(0, min(100, int(value))))
        self._save()

    @staticmethod
    def _reset_daily_counts(state: PetStateData) -> PetStateData:
        today = date.today().isoformat()
        if state.interaction_date == today:
            return state
        return replace(
            state,
            interaction_date=today,
            chat_count=0,
            headpat_count=0,
            click_count=0,
        )

    def _save(self) -> None:
        if self.store is None:
            return
        try:
            self.store.save(self.state)
        except Exception:
            return
