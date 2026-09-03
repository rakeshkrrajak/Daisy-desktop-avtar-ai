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
default) and holds up her water bottle for a sip, along with a "drink water"
speech bubble, then continues on her way to the left, walking off-screen and
disappearing until the next reminder.

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
**Reminders enabled** to turn scheduled reminders on or off, and
**Daisy Settings...** to configure walking and active hours. **Quit** exits
the app.

### Daisy Settings

Opened from the tray menu (or by right-clicking Daisy), this dialog lets you
configure:

- **Remind me to drink every** — the reminder interval in minutes, any value
  from 1 to 240 (for example, 5 minutes for quick testing).
- **Enable walking animations** — turn the reminder walk-in/out and ambient
  wandering on or off. If turned off, reminders just wave in place instead.
- **Act like drinking at** — how far across the screen (as a percentage of
  the full right-to-left crossing) Daisy walks before she stops to act out
  the reminder. 40% by default.
- **Wander every (min/max minutes)** — how often Daisy ambiently strolls
  across the screen between reminders, just for fun.
- **Seconds to cross the screen** — how fast she walks.
- **Restrict Daisy to active hours** — with a start/end time, Daisy (and her
  reminders) are hidden outside that window. Supports overnight ranges
  (e.g. 22:00 to 06:00).
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

## Troubleshooting

On a high-DPI display, Daisy may look too small or oversized. Edit `scale` in
`config.json` (for example, set it to `1.5`) to adjust her size; the change
takes effect after restarting the app.
