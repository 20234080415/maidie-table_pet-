"""Maidie 的时间感知、陪伴节奏与小时事件。

TimeManager 不直接操作 Qt、动画或 Agent。它只提供可注入的时间上下文，并在每个
自然小时至多产生一次经过冷却的陪伴事件，由 PetController 统一决定是否执行。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from random import choice
from typing import Any, Callable, Sequence


@dataclass(frozen=True, slots=True)
class TimeContext:
    """一次可供 UI 与 Agent 使用的时间快照。"""

    current_time: str
    period: str
    last_interaction: str | None
    days_together: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TimeEvent:
    """一个声明式时间陪伴事件，不直接触发消息或动画。"""

    kind: str
    period: str
    message: str
    animation: str = "idle"

    @property
    def agent_prompt(self) -> str:
        return (
            "这是 Maidie 的内部时间陪伴事件，不要机械报时，也不要提到系统事件。"
            f"当前时段是 {self.period}，请参考“{self.message}”的感觉，"
            "用一句简短、自然、温柔且不打扰用户的话主动陪伴。"
        )


class TimeManager:
    """提供生活化时间感知，并保守地产生每小时陪伴候选。"""

    PERIOD_GUIDANCE = {
        "morning": "语气清新一点，可以早安或轻轻鼓励，但不要催促。",
        "noon": "自然关心吃饭和补充水分，不要像健康软件通知。",
        "afternoon": "适合提醒伸展、看看远处或短暂休息。",
        "evening": "适合轻声问问今天过得怎么样，给用户留出不回答的空间。",
        "night": "语气更轻、更慢，提醒休息，不说教也不制造焦虑。",
    }

    EVENT_POOLS: dict[str, tuple[tuple[str, str, str], ...]] = {
        "morning": (
            ("morning_greeting", "早呀，我已经醒啦。今天也慢慢来就好。", "happy"),
            ("encouragement", "新的一天开始了，我会安安静静陪着你的。", "happy"),
            ("encouragement", "先不用急着把所有事都做好，我们一点点来。", "shy"),
        ),
        "noon": (
            ("meal_reminder", "到中午啦，有空记得吃点东西，我可以等你。", "idle"),
            ("meal_reminder", "先给自己补充一点能量吧，回来我还在这里。", "happy"),
            ("meal_reminder", "忙到这里已经很认真了，要不要先去吃饭？", "shy"),
        ),
        "afternoon": (
            ("break_reminder", "下午也辛苦啦，要不要伸个懒腰再继续？", "shy"),
            ("break_reminder", "眼睛也需要喘口气，看看远一点的地方吧。", "idle"),
            ("break_reminder", "先停一小会儿也没关系，我陪你一起发会儿呆。", "sleepy"),
        ),
        "evening": (
            ("day_checkin", "今天过得怎么样？想说的话，我会认真听。", "shy"),
            ("day_checkin", "一天快慢慢收尾了，有没有什么想和我讲的？", "idle"),
            ("day_checkin", "无论今天顺不顺利，你都已经走到这里啦。", "happy"),
        ),
        "night": (
            ("sleep_reminder", "夜深啦，剩下的事情明天再做也可以。", "sleepy"),
            ("sleep_reminder", "我有一点困了，你也别陪电脑太久呀。", "sleepy"),
            ("sleep_reminder", "该让今天轻轻结束啦，我会陪你到准备休息。", "sleepy"),
        ),
    }

    def __init__(
        self,
        *,
        cooldown_seconds: float = 90 * 60,
        quiet_after_interaction_seconds: float = 15 * 60,
        now_provider: Callable[[], datetime] | None = None,
        choice_fn: Callable[[Sequence[tuple[str, str, str]]], tuple[str, str, str]]
        | None = None,
    ) -> None:
        self.cooldown_seconds = max(60 * 60, float(cooldown_seconds))
        self.quiet_after_interaction_seconds = max(
            60.0, float(quiet_after_interaction_seconds)
        )
        self._now_provider = now_provider or (lambda: datetime.now().astimezone())
        self._choice = choice_fn or choice
        self._last_interaction: datetime | None = None
        self._last_event_at: datetime | None = None
        self._observed_hour: datetime | None = None
        self._last_message = ""

    def current_time(self, now: datetime | None = None) -> datetime:
        current = now or self._now_provider()
        return current.astimezone() if current.tzinfo is None else current

    @staticmethod
    def period_for(value: datetime) -> str:
        hour = value.hour
        if 5 <= hour < 11:
            return "morning"
        if 11 <= hour < 14:
            return "noon"
        if 14 <= hour < 18:
            return "afternoon"
        if 18 <= hour < 23:
            return "evening"
        return "night"

    def mark_interaction(self, now: datetime | None = None) -> None:
        self._last_interaction = self.current_time(now)

    def mark_proactive_activity(self, now: datetime | None = None) -> None:
        """让其他主动消息与时间提醒共享安静期，避免连续弹出。"""

        current = self.current_time(now)
        self._last_event_at = current
        self._observed_hour = current.replace(minute=0, second=0, microsecond=0)

    def context(
        self, first_meet_time: datetime, now: datetime | None = None
    ) -> TimeContext:
        current = self.current_time(now)
        first_meet, current = self._compatible_pair(first_meet_time, current)
        days_together = max(0, int((current - first_meet).total_seconds())) // (
            24 * 60 * 60
        )
        last_interaction = self._last_interaction
        return TimeContext(
            current_time=current.isoformat(timespec="seconds"),
            period=self.period_for(current),
            last_interaction=(
                last_interaction.isoformat(timespec="seconds")
                if last_interaction is not None
                else None
            ),
            days_together=days_together,
        )

    def agent_context(
        self, first_meet_time: datetime, now: datetime | None = None
    ) -> dict[str, Any]:
        snapshot = self.context(first_meet_time, now)
        return {
            "time_context": snapshot.to_dict(),
            "time_guidance": self.PERIOD_GUIDANCE[snapshot.period],
            "event_type": "internal",
        }

    def poll_hourly_event(self, now: datetime | None = None) -> TimeEvent | None:
        """每个自然小时只评估一次，并用全局冷却避免连续打扰。"""

        current = self.current_time(now)
        hour_slot = current.replace(minute=0, second=0, microsecond=0)
        if self._observed_hour is None:
            self._observed_hour = hour_slot
            return None
        if hour_slot <= self._observed_hour:
            return None
        self._observed_hour = hour_slot
        if (
            self._last_event_at is not None
            and (current - self._last_event_at).total_seconds() < self.cooldown_seconds
        ):
            return None
        if (
            self._last_interaction is not None
            and (current - self._last_interaction).total_seconds()
            < self.quiet_after_interaction_seconds
        ):
            return None
        period = self.period_for(current)
        pool = tuple(
            event for event in self.EVENT_POOLS[period] if event[1] != self._last_message
        ) or self.EVENT_POOLS[period]
        kind, message, animation = self._choice(pool)
        self._last_event_at = current
        self._last_message = message
        return TimeEvent(kind, period, message, animation)

    def should_use_sleepy_animation(
        self, idle_seconds: float, now: datetime | None = None
    ) -> bool:
        """深夜短暂空闲或晚间长时间低活跃时，允许表现出困倦。"""

        period = self.period_for(self.current_time(now))
        idle = max(0.0, float(idle_seconds))
        return (period == "night" and idle >= 5 * 60) or (
            period == "evening" and idle >= 30 * 60
        )

    @staticmethod
    def companion_time(
        first_meet_time: datetime, now: datetime | None = None
    ) -> tuple[int, int]:
        current = now or datetime.now(first_meet_time.tzinfo)
        first_meet, current = TimeManager._compatible_pair(first_meet_time, current)
        elapsed = max(0, int((current - first_meet).total_seconds()))
        days, remainder = divmod(elapsed, 24 * 60 * 60)
        hours = remainder // (60 * 60)
        return days, hours

    def companion_time_text(
        self, first_meet_time: datetime, now: datetime | None = None
    ) -> str:
        days, hours = self.companion_time(first_meet_time, now)
        return f"{days}天{hours}小时"

    @staticmethod
    def _compatible_pair(
        first: datetime, current: datetime
    ) -> tuple[datetime, datetime]:
        if first.tzinfo is None and current.tzinfo is not None:
            current = current.replace(tzinfo=None)
        elif first.tzinfo is not None and current.tzinfo is None:
            current = current.replace(tzinfo=first.tzinfo)
        return first, current
