# Denim Daisy

Denim Daisy is a tiny Windows desktop pet that reminds you to drink water. It
runs locally and makes no network calls.

## Install and run

1. Install Python 3.11 or newer.
2. Open Command Prompt in this folder.
3. Create a virtual environment:

   ```text
   python -m venv .venv
   ```

4. Activate it and install the pinned dependencies:

   ```text
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. Launch with `run_daisy.bat`, or run `python -m daisy_pet`.

The pet floats above other windows. Drag it with the left mouse button. A
single click shows the approximate time until the next reminder. A
**right-click on Daisy herself** also opens the same menu as the tray icon
(handy if you can't find the tray icon — see note below). A **double-click
on Daisy** instantly dismisses her — whatever she's doing (idle, walking,
mid-reminder) — and she reappears at the next reminder or ambient wander
like normal.

Every so often Daisy wanders across the screen along the top of your
taskbar just for fun. When a water reminder is due (on your configured
interval), she walks in from the right edge, stops partway across (40% by
default) and holds up her water bottle for a sip. She waits for your choice:
**I drank it** records the sip, while **Snooze 5 min** postpones this reminder.
If the choice bubble expires, the reminder is counted as ignored. Daisy then
walks back out to the left and disappears until the next reminder. She always
appears in the right corner and walks right-to-left, with her feet on the
taskbar line. The **Snooze 10 minutes** tray command remains separate.

## Tray menu

The tray menu opens with either a left-click or a right-click on Daisy's tray
icon (or a right-click on Daisy herself).

> **Can't find the tray icon?** Windows often auto-hides new tray icons
> behind the `^` "show hidden icons" chevron near the clock. Click that
> chevron, find Daisy, and optionally drag her icon out (or use Windows
> Settings → Personalization → Taskbar → "Select which icons appear on the
> taskbar" to always show her).

The tray menu provides **Drink now**, **Snooze 10 minutes** (for the water
reminder), a **Snooze a reminder** submenu (for your custom reminders — see
below), an **Interval** submenu with 15, 30, 45, and 60 minutes,
**Reminders enabled** to turn scheduled reminders on or off,
**Today's summary** to hear Daisy's recap of your day right now,
**Add a note...** to jot down a line she should remember, and
**Daisy Settings...** to configure walking and active hours. **Quit** exits
the app.

### Daisy Settings

Opened from the tray menu (or by right-clicking Daisy), this dialog groups
its settings into tabs — **Water**, **Daisy**, **My desk**, **Memory**,
**Reminders** and **Advanced** — so **OK** and **Cancel** stay in reach on
any screen, and a knob is greyed out while the feature that owns it is
switched off.

**Water**

- **Remind me to drink every** — the reminder interval in minutes, any value
  from 1 to 240 (for example, 5 minutes for quick testing).
- **Wait for my answer** — how long Daisy waits at the drink point
  for **I drank it** or **Snooze 5 min** before treating the reminder as
  ignored.
- **Enable mood expressions** — let her tone and pose follow how you have
  been answering.
- **Restrict Daisy to active hours** — with a start/end time, Daisy (and her
  reminders) are hidden outside that window. Supports overnight ranges
  (e.g. 22:00 to 06:00).

**Daisy**

- **Daisy size** — choose a scale from 0.5× to 3.0×. Daisy resizes
  immediately when you accept the settings.
- **Enable walking animations** — turn the reminder walk-in/out and ambient
  wandering on or off. If turned off, reminders just wave in place instead.
- **Wander every (min/max minutes)** — how often Daisy ambiently strolls
  across the screen between reminders, just for fun.
- **Enable lifelike idle behaviour** — let her occasionally play a quiet,
  pose-only idle animation.

**My desk**

- **Enable activity awareness** — allow Daisy to notice local
  foreground-window activity and offer occasional comments.
- **Suggest closing stale browser tabs**, **Stale tab age** and
  **Minimum browser windows** — when she should bring up old tabs.
- **Walk me through stale tabs** — let Daisy guide you through each stale tab
  so you can choose whether to keep it or close it.

**Memory**

- **Remember my day (local only)** — turn Daisy's local memory (app time,
  hydration, tab decisions, notes) on or off.
- **Bring me a daily summary** and **Summary at** — whether Daisy walks in
  with a recap of your day, and the time she does it (18:00 by default).
- **Keep memories for** — how long she keeps her local rows before pruning
  them, 1 to 365 days (30 by default).

**Reminders**

- **Custom reminders** — a list where you can **Add...** your own reminders
  (any text, like "Stretch", "Stand up", "Eat lunch"). Each one fires either:
  - **Repeat every** N minutes (like the water reminder), or
  - **At a specific time** — pick an exact clock time (e.g. 15:00) and it
    fires once a day at that time, then automatically rolls over to the
    same time tomorrow.

  Each reminder also has its own **Snooze by** duration (in minutes), used
  when you snooze it from the tray's **Snooze a reminder** submenu.
  Check/uncheck an entry in the list to enable or disable it, or select one
  and click **Remove selected** to delete it. Custom reminders use the same
  walk-in cinematic as the water reminder (waving instead of drinking) and
  never overlap with it or each other — only one reminder plays out at a
  time, and others just wait their turn.

**Advanced** — the fine-tuning most people never touch: **Act like drinking
at** (how far across the screen she walks before acting out a reminder, 40%
by default), **Seconds to cross the screen**, the minimum and maximum delay
between idle poses, and the optional local Ollama lines with their URL and
model.

Speech bubbles use a colourful cartoon balloon with a directional tail rather
than a plain rectangle, and the tail flips when the balloon must appear below
the Daisy anchor.

Daisy's "drinking" pose (`daisy_pet/assets/drinking/01.png`) is a dedicated
illustration of her holding a water bottle, layered on top of the base
sprite sheet. If that image is ever missing, she automatically falls back to
her hands-clasped-near-her-chin pose with a small drawn glass of water
tilting over her hands instead, so the reminder still reads clearly either
way.

### Adding more custom poses

Beyond `drinking`, you can drop numbered, transparent-background PNGs (e.g.
`01.png`, `02.png`, ...) into any folder under `daisy_pet/assets/` and
register it in `CUSTOM_STATE_DIRS` in `daisy_pet/sprites.py` to use it as a
new animation state — no need to fit it into the packed spritesheet grid.
Frames are automatically scaled to fit and aligned to the same ground
baseline as her other poses.

Settings are saved immediately to
`%APPDATA%\DenimDaisy\config.json`.

## Start with Windows

Create a shortcut to `run_daisy.bat` in the Windows Startup folder. To open
that folder, press `Win+R`, enter `shell:startup`, and press Enter.

## Mood expressions

With moods enabled, Daisy uses expression poses based on what is happening:
happy after you acknowledge a sip, thinking after a snooze, disappointed after
repeated snoozes, waiting after repeated ignored reminders, sleepy late at
night, content on her first appearance of the day, surprised after dragging
her, and neutral otherwise. Reminder bubbles invite you to click after
drinking; clicking acknowledges the sip, while letting the bubble expire counts
as ignored.

## Optional: local AI lines with Ollama

Install Ollama locally and run `ollama pull llama3.2`, then enable the Ollama
option in **Daisy Settings**. It is off by default, only accepts localhost
connections, and nothing is sent anywhere else.

## Activity awareness

When enabled, Daisy checks the foreground window title, foreground process
name, local idle time, and the number of visible browser windows. She uses
those signals to offer occasional comments when a meeting or message appears,
you have many browser windows open, you have focused for 45 minutes, you return
from a long idle period, or you have been sitting for 90 minutes. Checks run
every 20 seconds and are entirely local, and nothing is ever sent anywhere.
With memory enabled, the foreground *process* name (like `code.exe`) is
aggregated into per-day totals on disk; window titles are never written down.
Turn off **Enable activity awareness** in **Daisy Settings** to
disable these checks. Exact browser *tab* counts are not detected; Daisy only
counts browser windows.

## Stale browser-tab hints

When enabled, Daisy keeps track of browser pages that have not been active for
the configured number of minutes and, when enough browser tabs or windows are
open, may suggest closing up to two of them. The hint is local and temporary:
tab titles and their last-active timestamps are held in memory only, never
written to the configuration, logged, or sent anywhere.

Per-tab titles require the optional Windows UI Automation package:

```text
pip install comtypes==1.4.16
```

`comtypes` is optional and MIT-licensed; it is not a required Daisy
dependency. Without it, Daisy falls back to one pseudo-tab per visible
browser window and counts browser windows rather than exact tabs. Disable
**Suggest closing stale browser tabs** in **Daisy Settings** to turn this
feature off.

When **Walk me through stale tabs** is enabled, Daisy offers a **Show me** or
**Later** choice after a stale-tab hint. With **Show me**, she walks to each
stale tab, points it out, and offers **Keep it** or **Next**. Daisy never
closes a browser tab herself and never sends a close keystroke; press
**Ctrl+W** yourself if you want to close the tab. **Keep it** remembers the
choice until the next day. The keep list stores only a salted-free, truncated
SHA-256 hash of the normalized title and the date. No plaintext browser titles
are stored on disk.

## Local memory and the daily summary

With **Remember my day (local only)** enabled, Daisy keeps a small SQLite file next
to her configuration, at `%APPDATA%\DenimDaisy\memory.sqlite3`. Nothing leaves
the laptop: there is no cloud, no telemetry, and no account.

What she stores:

- per-day foreground seconds per process name (for example `code.exe`),
  aggregated rather than one row per check;
- hydration outcomes — acknowledged, snoozed, ignored;
- stale-tab decisions — kept or closed — identified only by the same
  truncated SHA-256 hash of the normalized title used by the keep list;
- the notes you type yourself, with an optional due date.

What she never stores: window titles, browser tab titles, URLs, keystrokes, or
anything else in plaintext that came from a title. Rows older than **Keep
memories for** are pruned when Daisy starts.

**Today's summary** in the tray shows the recap on demand — something like
`Today: 4h in VS Code · 1h in Teams · 5 of 8 sips · 3 tabs kept · 2 notes`.
With **Bring me a daily summary** enabled she also walks in once a day at
**Summary at** to say it herself, using the same gates as the water
reminder: only while reminders are enabled and inside your active hours, and
never on top of a pending water choice or a stale-tab walkthrough. The wording
is generated offline; if Ollama is enabled it may rephrase the line, but the
offline template is always the fallback.

**Add a note...** opens a small box for one line — "call Manisha", "decided X
with Bhavana" — up to 200 characters, with an optional due date. Notes are
counted in the summary, and a note due today is read out in it.

## Lifelike idle behaviour

With **Enable lifelike idle behaviour**, Daisy occasionally plays a small
pose-only animation chosen for the time of day, then returns to idle. The
delay is randomized between the configured minimum and maximum seconds. A
rare, short line of idle chatter may appear, but chatter is rate-limited and
never replaces the water reminders.

Daisy pauses these idle poses while a reminder walk or speech bubble is active,
when the schedule is inactive, during a meeting title, or after a long period
of user inactivity. Turn off **Enable lifelike idle behaviour** in **Daisy
Settings** to disable it.

## Troubleshooting

On a high-DPI display, Daisy may look too small or oversized. Edit `scale` in
`config.json` (for example, set it to `1.5`) to adjust her size; the change
takes effect after restarting the app.
