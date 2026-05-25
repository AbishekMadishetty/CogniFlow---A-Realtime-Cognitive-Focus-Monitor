"""
CogniFlow — Alert Sound
Plays different tones for different alert types.
Uses winsound — built into Python on Windows, no install needed.
"""

import threading
import winsound

# (frequency Hz, duration ms) sequences per alert type
SOUNDS = {
    "warning": [(600, 150), (500, 150), (600, 200)],
    "blocked": [(900, 100), (900, 100), (900, 100), (500, 400)],
    "sleep":   [(400, 300), (350, 300), (300, 500)],
    "break":   [(523, 150), (659, 150), (784, 300)],
    "info":    [(700, 100), (800, 200)],
}


def play(alert_type="info"):
    """Play alert sound in background thread — never blocks UI."""
    threading.Thread(
        target=_play_tones,
        args=(SOUNDS.get(alert_type, SOUNDS["info"]),),
        daemon=True
    ).start()


def _play_tones(tones):
    try:
        for freq, duration in tones:
            winsound.Beep(freq, duration)
    except Exception:
        try:
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass
