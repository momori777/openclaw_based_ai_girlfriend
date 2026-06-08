from __future__ import annotations

from dataclasses import dataclass

PROACTIVE_DEFAULT_CHECK_INTERVAL_MINUTES = 2
PROACTIVE_DEFAULT_COOLDOWN_MINUTES = 10
PROACTIVE_DEFAULT_SCREEN_CONTEXT_BATCH_LIMIT = 6
PROACTIVE_MIN_CHECK_INTERVAL_MINUTES = 1
PROACTIVE_MAX_CHECK_INTERVAL_MINUTES = 120
PROACTIVE_MIN_COOLDOWN_MINUTES = 1
PROACTIVE_MAX_COOLDOWN_MINUTES = 120
PROACTIVE_MIN_SCREEN_CONTEXT_BATCH_LIMIT = 1
PROACTIVE_MAX_SCREEN_CONTEXT_BATCH_LIMIT = 20
PROACTIVE_TIMER_POLL_INTERVAL_MS = 10_000
PROACTIVE_TIMER_DUE_GRACE_SECONDS = 1.0
PROACTIVE_SCREEN_CONTEXT_HISTORY_MARKER = "[已抓取屏幕上下文]"


@dataclass(frozen=True)
class ProactiveCareSettings:
    """主动关怀配置；由主动屏幕获取开关控制是否运行。"""

    enabled: bool = True
    screen_context_enabled: bool = True
    check_interval_minutes: int = PROACTIVE_DEFAULT_CHECK_INTERVAL_MINUTES
    cooldown_minutes: int = PROACTIVE_DEFAULT_COOLDOWN_MINUTES
    screen_context_batch_limit: int = PROACTIVE_DEFAULT_SCREEN_CONTEXT_BATCH_LIMIT

    def normalized(self) -> "ProactiveCareSettings":
        screen_context_enabled = self.screen_context_enabled
        return ProactiveCareSettings(
            enabled=screen_context_enabled,
            screen_context_enabled=screen_context_enabled,
            check_interval_minutes=_clamp_interval_minutes(
                self.check_interval_minutes,
                min_value=PROACTIVE_MIN_CHECK_INTERVAL_MINUTES,
                max_value=PROACTIVE_MAX_CHECK_INTERVAL_MINUTES,
            ),
            cooldown_minutes=_clamp_interval_minutes(
                self.cooldown_minutes,
                min_value=PROACTIVE_MIN_COOLDOWN_MINUTES,
                max_value=PROACTIVE_MAX_COOLDOWN_MINUTES,
            ),
            screen_context_batch_limit=_clamp_bounded_int(
                self.screen_context_batch_limit,
                min_value=PROACTIVE_MIN_SCREEN_CONTEXT_BATCH_LIMIT,
                max_value=PROACTIVE_MAX_SCREEN_CONTEXT_BATCH_LIMIT,
            ),
        )

    def allows_screen_context(self) -> bool:
        """允许主动获取屏幕信息时，主动关怀才会运行。"""
        return self.screen_context_enabled


def _clamp_interval_minutes(value: int, *, min_value: int, max_value: int) -> int:
    return _clamp_bounded_int(value, min_value=min_value, max_value=max_value)


def _clamp_bounded_int(value: int, *, min_value: int, max_value: int) -> int:
    return max(
        min_value,
        min(max_value, value),
    )
