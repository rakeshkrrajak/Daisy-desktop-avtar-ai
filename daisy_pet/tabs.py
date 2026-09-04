"""Optional local browser-tab probing and stale-tab observations."""

from __future__ import annotations

import random
import sys
import ctypes
from dataclasses import dataclass
from datetime import datetime, timedelta

from . import activity
from .lines import stale_tab_line


@dataclass(frozen=True)
class TabInfo:
    key: str
    title: str
    browser: str
    active: bool


@dataclass(frozen=True)
class TabSnapshot:
    tabs: tuple[TabInfo, ...]
    at: datetime
    source: str


def _probe_uia(
    windows: list[tuple[int, str, str]], foreground: int
) -> TabSnapshot | None:
    try:
        import comtypes.client

        automation = comtypes.client.CreateObject(
            "UIAutomationClient.CUIAutomation"
        )
        condition = automation.CreatePropertyCondition(30003, 50019)
        result: list[TabInfo] = []
        for window_id, window_title, browser in windows:
            try:
                root = automation.ElementFromHandle(window_id)
                elements = root.FindAll(4, condition)
                for index in range(elements.Length):
                    element = elements.GetElement(index)
                    title = str(element.CurrentName or "")
                    if not title:
                        continue
                    try:
                        selected = bool(element.GetCurrentPropertyValue(30079))
                    except (AttributeError, OSError, TypeError):
                        selected = index == 0
                    result.append(_tab_info(
                        window_id, title, browser, selected, foreground
                    ))
            except (AttributeError, OSError, TypeError):
                continue
        if result:
            return TabSnapshot(tuple(result), datetime.now(), "uia")
    except Exception:
        pass
    return None


def _tab_info(
    window_id: int,
    title: str,
    browser: str,
    selected: bool,
    foreground: int,
) -> TabInfo:
    return TabInfo(
        f"{window_id}:{title}",
        title,
        browser,
        selected and window_id == foreground,
    )


def probe_tabs() -> TabSnapshot | None:
    if sys.platform != "win32":
        return None
    now = datetime.now()
    try:
        windows = activity.browser_windows()
        try:
            foreground = int(ctypes.windll.user32.GetForegroundWindow())
        except (AttributeError, OSError, TypeError):
            foreground = 0
        uia = _probe_uia(windows, foreground)
        if uia is not None:
            return uia
        return TabSnapshot(
            tuple(
                TabInfo(f"{window_id}:{title}", title, browser, window_id == foreground)
                for window_id, title, browser in windows
            ),
            now,
            "windows",
        )
    except (AttributeError, OSError, TypeError):
        return TabSnapshot((), now, "windows")


class TabWatcher:
    def __init__(
        self,
        idle_minutes: int = 60,
        min_open: int = 8,
        cooldown_minutes: int = 30,
        repeat_minutes: int = 120,
        rng: random.Random | None = None,
    ) -> None:
        self.idle_duration = timedelta(minutes=idle_minutes)
        self.min_open = min_open
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.repeat = timedelta(minutes=repeat_minutes)
        self.rng = rng
        self.last_active: dict[str, datetime] = {}
        self._last_mentioned: dict[str, datetime] = {}
        self._last_emit: datetime | None = None

    def observe(self, snapshot: TabSnapshot) -> activity.Observation | None:
        current_keys = {tab.key for tab in snapshot.tabs}
        self.last_active = {
            key: value
            for key, value in self.last_active.items()
            if key in current_keys
        }
        self._last_mentioned = {
            key: value
            for key, value in self._last_mentioned.items()
            if key in current_keys
        }
        for tab in snapshot.tabs:
            if tab.key not in self.last_active:
                self.last_active[tab.key] = snapshot.at
            if tab.active:
                self.last_active[tab.key] = snapshot.at

        if len(snapshot.tabs) < self.min_open:
            return None
        stale = [
            tab
            for tab in snapshot.tabs
            if snapshot.at - self.last_active[tab.key] >= self.idle_duration
            and (
                tab.key not in self._last_mentioned
                or snapshot.at - self._last_mentioned[tab.key] >= self.repeat
            )
        ]
        if not stale:
            return None
        if (
            self._last_emit is not None
            and snapshot.at - self._last_emit < self.cooldown
        ):
            return None
        if len(stale) > 2:
            chooser = self.rng or random
            chosen_tabs = chooser.sample(stale, 2)
        else:
            chosen_tabs = stale
        chosen = [tab.title for tab in chosen_tabs]
        age = min(
            snapshot.at - self.last_active[tab.key] for tab in chosen_tabs
        )
        minutes = max(1, int(age.total_seconds() // 60))
        self._last_emit = snapshot.at
        for tab in chosen_tabs:
            self._last_mentioned[tab.key] = snapshot.at
        return activity.Observation(
            "stale_tabs",
            stale_tab_line(chosen, minutes, self.rng),
            activity.TONE_FOR_KIND["stale_tabs"],
        )
