from __future__ import annotations

from dataclasses import replace

from core.pet_state import PetStateData


class AffectionSystem:
    """Calculate relationship growth without coupling it to Qt."""

    INTERACTION_GAINS = {
        "chat": 2,
        "headpat": 3,
        "click": 1,
    }
    RELATIONSHIPS = (
        (90, "特别伙伴"),
        (70, "信赖"),
        (45, "朋友"),
        (20, "熟悉"),
        (0, "初识"),
    )

    def apply_interaction(self, state: PetStateData, interaction: str) -> PetStateData:
        gain = self.INTERACTION_GAINS.get(interaction, 0)
        affection = max(0, min(100, state.affection + gain))
        level = max(1, min(10, affection // 10 + 1))
        return replace(
            state,
            affection=affection,
            level=level,
            interaction_count=state.interaction_count + 1,
        )

    def relationship_for(self, affection: int) -> str:
        value = max(0, min(100, int(affection)))
        for threshold, label in self.RELATIONSHIPS:
            if value >= threshold:
                return label
        return "初识"
