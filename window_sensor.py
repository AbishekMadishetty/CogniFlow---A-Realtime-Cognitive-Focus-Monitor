"""
CogniFlow — Window Sensor
Detects active app + section from window title.
Uses Windows API via ctypes — no extra packages needed.

Examples:
  Chrome + "Gmail"
  VS Code + "engine.py (cogniflow)"
  Chrome + "YouTube → video title"
"""

import ctypes   
import ctypes.wintypes
import re


# ── Per-app title parsers ─────────────────────────────────────────────────────
# Inside window_sensor.py
class WindowSensor:
    def __init__(self, shutdown_event):
        # your code here
        pass

    def start(self):
        # your code here
        pass

def _parse_chrome(title):
    title = re.sub(r'\s*-\s*Google Chrome$', '', title).strip()
    return _classify_web_page(title)

def _parse_edge(title):
    title = re.sub(r'\s*-\s*Microsoft Edge$', '', title).strip()
    return _classify_web_page(title)

def _parse_firefox(title):
    title = re.sub(r'\s*[—–-]\s*Mozilla Firefox$', '', title).strip()
    return _classify_web_page(title)

def _classify_web_page(page_title):
    t = page_title.lower()
    if "google search" in t or (t.startswith("google") and len(t) < 30):
        return "Google Search"
    if "gmail" in t or "inbox" in t:         return "Gmail"
    if "google docs" in t:                   return "Google Docs"
    if "google sheets" in t:                 return "Google Sheets"
    if "google meet" in t:                   return "Google Meet"
    if "google drive" in t:                  return "Google Drive"
    if "google maps" in t:                   return "Google Maps"
    if "youtube" in t:
        video = re.sub(r'\s*[-–]\s*youtube.*$', '', page_title,
                       flags=re.IGNORECASE).strip()
        return f"YouTube → {video[:40]}" if video else "YouTube"
    if "twitter" in t or "x.com" in t:      return "Twitter / X"
    if "linkedin" in t:                      return "LinkedIn"
    if "facebook" in t:                      return "Facebook"
    if "instagram" in t:                     return "Instagram"
    if "reddit" in t:                        return "Reddit"
    if "whatsapp" in t:                      return "WhatsApp Web"
    if "slack" in t:                         return "Slack"
    if "discord" in t:                       return "Discord"
    if "notion" in t:                        return "Notion"
    if "github" in t:                        return "GitHub"
    if "stackoverflow" in t:                 return "Stack Overflow"
    if "localhost" in t or "127.0.0.1" in t: return "Localhost"
    if "claude" in t:                        return "Claude AI"
    if "chatgpt" in t:                       return "ChatGPT"
    if "medium" in t:                        return "Medium"
    if "wikipedia" in t:                     return "Wikipedia"
    return page_title[:50] if page_title else "Browser"

def _parse_vscode(title):
    title = re.sub(r'\s*-\s*Visual Studio Code$', '', title).strip()
    parts = [p.strip() for p in title.split(' - ')]
    if len(parts) >= 2:
        return f"{parts[0]}  ({parts[1]})"
    return title[:50] if title else "VS Code"

def _parse_explorer(title):
    if not title or title.lower() in ("file explorer", "home"):
        return "File Explorer"
    return f"Folder: {title}"

def _parse_generic(title):
    if not title:
        return ""
    title = re.sub(
        r'\s*[-–—]\s*(Microsoft Word|Excel|PowerPoint|Notepad\+\+|Sublime Text|Atom)$',
        '', title, flags=re.IGNORECASE
    ).strip()
    return title[:50]


# ── App registry ──────────────────────────────────────────────────────────────

APP_MAP = {
    "chrome":    ("Chrome",      _parse_chrome),
    "msedge":    ("Edge",        _parse_edge),
    "firefox":   ("Firefox",     _parse_firefox),
    "code":      ("VS Code",     _parse_vscode),
    "explorer":  ("Explorer",    _parse_explorer),
    "notepad":   ("Notepad",     _parse_generic),
    "slack":     ("Slack",       _parse_generic),
    "discord":   ("Discord",     _parse_generic),
    "zoom":      ("Zoom",        _parse_generic),
    "teams":     ("Teams",       _parse_generic),
    "winword":   ("Word",        _parse_generic),
    "excel":     ("Excel",       _parse_generic),
    "powerpnt":  ("PowerPoint",  _parse_generic),
    "pycharm64": ("PyCharm",     _parse_generic),
    "pycharm":   ("PyCharm",     _parse_generic),
    "obsidian":  ("Obsidian",    _parse_generic),
    "notion":    ("Notion",      _parse_generic),
    "spotify":   ("Spotify",     _parse_generic),
    "vlc":       ("VLC",         _parse_generic),
}


# ── Main functions ────────────────────────────────────────────────────────────

def get_active_window():
    """Returns (app_display_name, section)"""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()

        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf    = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or ""

        pid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        import psutil
        try:
            proc     = psutil.Process(pid.value)
            proc_key = proc.name().lower().replace(".exe", "")
        except Exception:
            proc_key = "unknown"

        if proc_key in APP_MAP:
            display_name, parser = APP_MAP[proc_key]
            section = parser(title)
        else:
            display_name = proc_key.capitalize()
            section      = _parse_generic(title)

        return display_name, section

    except Exception:
        return "Unknown", ""


def get_activity_label(app, section):
    """e.g. 'Chrome  →  Gmail'"""
    if section:
        return f"{app}  →  {section}"
    return app
