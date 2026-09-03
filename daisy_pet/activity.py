"""Local Windows activity probing and deterministic observation rules."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .lines import OBSERVATION_LINES

BROWSER_PROCESSES = {"chrome.exe", "msedge.exe", "firefox.exe"}
MEETING_HINTS = ("microsoft teams", "meeting", "zoom meeting")
MESSAGE_HINTS = ("new message", "chat |")


@dataclass(frozen=True)
class WindowInfo:
    title: str
    process: str


@dataclass(frozen=True)
class ActivitySnapshot:
    window: WindowInfo
    idle_seconds: float
    browser_window_count: int
    at: datetime


def _window_title(user32, hwnd) -> str:
    try:
        buffer = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value
    except (AttributeError, OSError, TypeError):
        return ""


def _process_name(user32, kernel32, hwnd) -> str:
    try:
        process_id = wintypes.DWORD()
        if not user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id)):
            return ""
        process = kernel32.OpenProcess(0x1000, False, process_id.value)
        if not process:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(512)
            size = wintypes.DWORD(len(buffer))
            if not kernel32.QueryFullProcessImageNameW(
                process, 0, buffer, ctypes.byref(size)
            ):
                return ""
            return Path(buffer.value).name.lower()
        finally:
            try:
                kernel32.CloseHandle(process)
            except (AttributeError, OSError):
                pass
    except (AttributeError, OSError, TypeError):
        return ""


def _safe_windows_probe() -> ActivitySnapshot:
    now = datetime.now()
    title = ""
    process = ""
    idle_seconds = 0.0
    browser_window_count = 0
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
    except (AttributeError, OSError):
        return ActivitySnapshot(WindowInfo("", ""), 0.0, 0, now)

    try:
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            title = _window_title(user32, hwnd)
            process = _process_name(user32, kernel32, hwnd)
    except (AttributeError, OSError, TypeError):
        pass

    class LastInputInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("dwTime", wintypes.DWORD),
        ]

    try:
        last_input = LastInputInfo(ctypes.sizeof(LastInputInfo))
        if user32.GetLastInputInfo(ctypes.byref(last_input)):
            elapsed = (kernel32.GetTickCount() - last_input.dwTime) & 0xFFFFFFFF
            idle_seconds = elapsed / 1000.0
    except (AttributeError, OSError, TypeError):
        pass

    try:
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def visit(hwnd, _lparam):
            nonlocal browser_window_count
            try:
                if user32.IsWindowVisible(hwnd):
                    window_process = _process_name(user32, kernel32, hwnd)
                    if window_process in BROWSER_PROCESSES:
                        browser_window_count += 1
            except (AttributeError, OSError, TypeError):
                pass
            return True

        user32.EnumWindows(callback_type(visit), 0)
    except (AttributeError, OSError, TypeError):
        pass

    return ActivitySnapshot(
        WindowInfo(title, process),
        idle_seconds,
        browser_window_count,
        now,
    )


def probe() -> ActivitySnapshot | None:
    if sys.platform != "win32":
        return None
    return _safe_windows_probe()


@dataclass(frozen=True)
class Observation:
    kind: str
    text: str
    tone: str


class ActivityWatcher:
    _COOLDOWNS = {
        "meeting": timedelta(minutes=20),
        "message": timedelta(minutes=20),
        "browser_sprawl": timedelta(minutes=20),
        "idle_return": timedelta(minutes=20),
        "long_focus": timedelta(minutes=45),
        "sitting": timedelta(minutes=45),
    }
    _MOODS = {
        "meeting": ("surprised", "playful"),
        "message": ("surprised", "playful"),
        "browser_sprawl": ("waiting", "firm"),
        "long_focus": ("thinking", "gentle"),
        "idle_return": ("content", "cheerful"),
        "sitting": ("thinking", "gentle"),
    }

    def __init__(
        self,
        browser_window_limit: int = 6,
        focus_minutes: int = 45,
        sitting_minutes: int = 90,
        idle_minutes: int = 10,
    ) -> None:
        self.browser_window_limit = browser_window_limit
        self.focus_duration = timedelta(minutes=focus_minutes)
        self.sitting_duration = timedelta(minutes=sitting_minutes)
        self.idle_duration = idle_minutes * 60
        self._foreground_process = ""
        self._foreground_since: datetime | None = None
        self._previous_meeting = False
        self._previous_message = False
        self._last_non_idle: datetime | None = None
        self._previous_idle_seconds = 0.0
        self._last_emitted: dict[str, datetime] = {}

    @staticmethod
    def _has_hint(title: str, hints: tuple[str, ...]) -> bool:
        lowered = title.lower()
        return any(hint in lowered for hint in hints)

    def _emit(
        self, kind: str, now: datetime
    ) -> Observation | None:
        previous = self._last_emitted.get(kind)
        if previous is not None and now - previous < self._COOLDOWNS[kind]:
            return None
        self._last_emitted[kind] = now
        _, tone = self._MOODS[kind]
        return Observation(kind, OBSERVATION_LINES[kind][0], tone)

    def observe(self, snapshot: ActivitySnapshot) -> Observation | None:
        now = snapshot.at
        meeting = self._has_hint(snapshot.window.title, MEETING_HINTS)
        message = self._has_hint(snapshot.window.title, MESSAGE_HINTS)
        if (
            meeting
            and not self._previous_meeting
            and (observation := self._emit("meeting", now)) is not None
        ):
            result = observation
        elif (
            message
            and not self._previous_message
            and (observation := self._emit("message", now)) is not None
        ):
            result = observation
        elif snapshot.browser_window_count > self.browser_window_limit:
            result = self._emit("browser_sprawl", now)
        else:
            result = None

        process = snapshot.window.process
        if process != self._foreground_process:
            self._foreground_process = process
            self._foreground_since = now
        if (
            result is None
            and self._foreground_since is not None
            and now - self._foreground_since >= self.focus_duration
        ):
            result = self._emit("long_focus", now)

        idle_return = (
            self._previous_idle_seconds >= self.idle_duration
            and snapshot.idle_seconds < 60
        )
        if result is None and idle_return:
            result = self._emit("idle_return", now)

        if snapshot.idle_seconds >= 300:
            self._last_non_idle = now
        elif self._last_non_idle is None:
            self._last_non_idle = now
        if (
            result is None
            and self._last_non_idle is not None
            and now - self._last_non_idle >= self.sitting_duration
        ):
            result = self._emit("sitting", now)

        self._previous_meeting = meeting
        self._previous_message = message
        self._previous_idle_seconds = snapshot.idle_seconds
        return result
