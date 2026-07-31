from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from core.pet import PetController
from core.time_manager import TimeManager


class TimeManagerTests(unittest.TestCase):
    def test_period_boundaries(self):
        manager = TimeManager()
        expected = {
            4: "night",
            5: "morning",
            10: "morning",
            11: "noon",
            13: "noon",
            14: "afternoon",
            17: "afternoon",
            18: "evening",
            22: "evening",
            23: "night",
        }
        for hour, period in expected.items():
            with self.subTest(hour=hour):
                self.assertEqual(
                    manager.period_for(datetime(2026, 7, 31, hour, tzinfo=timezone.utc)),
                    period,
                )

    def test_context_contains_interaction_and_days_together(self):
        now = datetime(2026, 7, 31, 15, 30, tzinfo=timezone.utc)
        first_meet = now - timedelta(days=23, hours=6)
        manager = TimeManager(now_provider=lambda: now)
        manager.mark_interaction(now - timedelta(minutes=12))

        context = manager.context(first_meet)

        self.assertEqual(context.period, "afternoon")
        self.assertEqual(context.days_together, 23)
        self.assertEqual(
            context.last_interaction,
            (now - timedelta(minutes=12)).isoformat(timespec="seconds"),
        )

    def test_hour_event_is_randomized_once_per_hour_and_cooled_down(self):
        picked = []

        def choose_last(pool):
            picked.append(tuple(pool))
            return pool[-1]

        start = datetime(2026, 7, 31, 8, 10, tzinfo=timezone.utc)
        manager = TimeManager(cooldown_seconds=3 * 60 * 60, choice_fn=choose_last)

        self.assertIsNone(manager.poll_hourly_event(start))
        first = manager.poll_hourly_event(start + timedelta(hours=1))
        self.assertIsNotNone(first)
        self.assertEqual(first.period, "morning")
        self.assertIsNone(manager.poll_hourly_event(start + timedelta(hours=1, minutes=30)))
        self.assertIsNone(manager.poll_hourly_event(start + timedelta(hours=2)))
        second = manager.poll_hourly_event(start + timedelta(hours=4))
        self.assertIsNotNone(second)
        self.assertEqual(second.period, "noon")
        self.assertEqual(len(picked), 2)

    def test_sleepy_animation_requires_night_or_low_evening_activity(self):
        manager = TimeManager()
        night = datetime(2026, 7, 31, 23, 30, tzinfo=timezone.utc)
        evening = datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc)
        afternoon = datetime(2026, 7, 31, 15, 0, tzinfo=timezone.utc)
        self.assertTrue(manager.should_use_sleepy_animation(300, night))
        self.assertTrue(manager.should_use_sleepy_animation(1800, evening))
        self.assertFalse(manager.should_use_sleepy_animation(60, evening))
        self.assertFalse(manager.should_use_sleepy_animation(7200, afternoon))

    def test_recent_interaction_and_other_proactive_activity_defer_event(self):
        start = datetime(2026, 7, 31, 10, 5, tzinfo=timezone.utc)
        manager = TimeManager(
            quiet_after_interaction_seconds=30 * 60,
            choice_fn=lambda pool: pool[0],
        )
        self.assertIsNone(manager.poll_hourly_event(start))
        manager.mark_interaction(start + timedelta(minutes=55))
        self.assertIsNone(manager.poll_hourly_event(start + timedelta(hours=1)))

        manager.mark_proactive_activity(start + timedelta(hours=2))
        self.assertIsNone(manager.poll_hourly_event(start + timedelta(hours=3)))
        event = manager.poll_hourly_event(start + timedelta(hours=4))
        self.assertIsNotNone(event)


class _Memory:
    def get_recent(self):
        return []

    def prompt_context(self):
        return ""

    def save(self, _message, _response):
        return None


class TimeManagerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_controller_injects_time_context_into_agent_request(self):
        now = datetime(2026, 7, 31, 20, 15, tzinfo=timezone.utc)
        manager = TimeManager(now_provider=lambda: now)
        controller = PetController(Mock(), _Memory(), time_manager=manager)
        controller._proactive_timer.stop()

        context, _reaction = controller._prepare_ai_request("今天有点累", False)
        time_payload = next(item for item in context if "time_context" in item)

        self.assertEqual(time_payload["time_context"]["period"], "evening")
        self.assertIn("time_guidance", time_payload)
        controller.shutdown()

    def test_controller_routes_hour_event_through_existing_agent_pipeline(self):
        start = datetime(2026, 7, 31, 11, 5, tzinfo=timezone.utc)
        now = [start]
        manager = TimeManager(
            now_provider=lambda: now[0],
            choice_fn=lambda pool: pool[0],
        )
        runtime = Mock()
        runtime.engine.enabled = True
        controller = PetController(
            Mock(),
            _Memory(),
            proactive_runtime=runtime,
            time_manager=manager,
        )
        controller._proactive_timer.stop()
        controller.submit_text = Mock()
        manager.poll_hourly_event(start)
        now[0] = start + timedelta(hours=1)

        controller._complete_proactive_result(({"idle_time": 0}, None))

        prompt = controller.submit_text.call_args.args[0]
        self.assertIn("不要机械报时", prompt)
        controller.submit_text.assert_called_once_with(prompt, proactive=True)
        controller.shutdown()


if __name__ == "__main__":
    unittest.main()
