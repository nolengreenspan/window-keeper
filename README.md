# Window Keeper

Keeps ordinary windows from hanging under the Windows taskbar.

Windows 11 has no "lock the taskbar" setting, and an app may place its window
anywhere. This small background script fixes the result instead: every 2
seconds it moves up any window whose bottom edge is below the usable area of its
screen.

## What it does and does not touch

- Moves a window **up only**, by exactly the overlap. Never resizes.
- Skips maximized, minimized, full-screen, hidden and tool windows.
- Skips a window taller than the usable area, since it cannot fit.
- Does nothing while the left mouse button is down, so dragging is never fought.
  A window dragged low is lifted back about 2 seconds after release.
- Works per screen, so a second monitor is handled too.
- The Desktop Dashboard panel is not affected: it is attached to the desktop
  layer, not an ordinary window.

## Files

| File | Purpose |
| --- | --- |
| `window_keeper.py` | The whole program. No packages needed. |
| `Window Keeper.lnk` (Startup folder) | Starts it at login, quietly |

## Run it

- Background: `pythonw window_keeper.py` (a second copy exits at once)
- One check, with output: `python window_keeper.py --once`
- Stop it: end `pythonw.exe` running `window_keeper.py` in Task Manager, and
  delete `Window Keeper.lnk` from
  `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` to stop it at login.

## Tested

19 Nov 2026: Outlook pushed 100 px below the taskbar was back at the usable
edge within 5 seconds with the helper running in the background.
