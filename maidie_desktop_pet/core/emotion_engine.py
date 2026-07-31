from __future__ import annotations


class EmotionEngine:
    """Translate the existing experience emotion into status-panel language."""

    DISPLAY_NAMES = {
        "happy": "开心",
        "speaking": "开心",
        "thinking": "平静",
        "shy": "害羞",
        "concern": "担心",
        "failed": "有点沮丧",
        "idle": "平静",
    }

    def display_mood(self, emotion: str, *, energy: int = 100) -> str:
        if int(energy) <= 25:
            return "困倦"
        return self.DISPLAY_NAMES.get(str(emotion or "idle"), "平静")

    def apply_interaction(self, mood: int, interaction: str) -> int:
        delta = {"chat": 2, "headpat": 5, "click": 1}.get(interaction, 0)
        return max(0, min(100, int(mood) + delta))
