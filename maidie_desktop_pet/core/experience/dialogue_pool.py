"""集中管理 Experience 层的短句与情境化随机选择。

Behavior/Proactive 组件按 key 请求短句，DialoguePool 负责去重复和注入随机选择器；
这些反馈不替代 Brain Synthesizer 的正式回答。
"""

from __future__ import annotations

import random
from typing import Callable


class DialoguePool:
    """Pure-Python event dialogue selector with per-event repeat avoidance."""

    DEFAULTS = {
        "fence_enabled": (
            "这是给我划的活动范围吗？", "好，我就在这里活动。",
            "范围收到，我会注意边界。", "放心，我不会乱跑。",
            "这里就是我的活动区了，对吧？",
        ),
        "fence_disabled": (
            "范围解除了，那我去四处看看。", "自由活动了。",
            "那我可以到处走走了吧？", "外面确实更舒服。",
            "好，我继续巡逻。",
        ),
        "fence_snapback": (
            "怎么又被弹回来了？", "就差一点点。",
            "明白，我不越界。", "这个边界还挺严格。",
            "好，我回来了。",
        ),
        "fence_edge_complain": (
            "这边不能走了吗？", "围栏在提醒我回头。", "这里像有一道空气墙。",
            "知道了，我不往外走。", "边界就在这里，对吧？",
        ),
    }

    def __init__(self, pools: dict[str, tuple[str, ...]] | None = None,
                 chooser: Callable[[tuple[str, ...]], str] = random.choice) -> None:
        self._pools = dict(self.DEFAULTS)
        if pools:
            self._pools.update({key: tuple(values) for key, values in pools.items()})
        self._chooser = chooser
        self._last: dict[str, str] = {}
        self.last_avoided_repeat = False

    def get(self, event: str) -> str:
        phrases = self._pools.get(event, ())
        if not phrases:
            raise KeyError(f"unknown dialogue event: {event}")
        previous = self._last.get(event)
        candidates = tuple(value for value in phrases if value != previous)
        self.last_avoided_repeat = previous is not None and len(phrases) > 1
        selected = self._chooser(candidates or phrases)
        self._last[event] = selected
        return selected

    def phrases(self, event: str) -> tuple[str, ...]:
        return self._pools.get(event, ())
