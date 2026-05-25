"""
CogniFlow — Keyboard Sensor
Tracks typing rhythm via keystroke flight times.
Never records WHAT keys are pressed — only WHEN.
"""

import time
import threading
import statistics
from pynput import keyboard


MAX_FLIGHT_TIME    = 2.0   # ignore gaps longer than this (user paused)
MAX_SAMPLES        = 20    # rolling window of flight times
STATE_TYPING_SEC   = 3.0   # idle < 3s = typing
STATE_READING_SEC  = 30.0  # idle 3-30s = reading, else = thinking


class KeyboardSensor:

    def __init__(self):
        self._lock         = threading.Lock()
        self._flight_times = []
        self._last_key_at  = 0.0
        self._listener     = None

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()
        print("[Keyboard] Listener started.")

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_press(self, key):
        now = time.time()
        with self._lock:
            if self._last_key_at > 0:
                gap = now - self._last_key_at
                if gap < MAX_FLIGHT_TIME:
                    self._flight_times.append(gap)
                    if len(self._flight_times) > MAX_SAMPLES:
                        self._flight_times = self._flight_times[-MAX_SAMPLES:]
            self._last_key_at = now

    def get_variance(self):
        with self._lock:
            if len(self._flight_times) < 2:
                return 0.0
            return statistics.variance(self._flight_times)

    def get_state(self):
        with self._lock:
            if self._last_key_at == 0:
                return "thinking"
            idle = time.time() - self._last_key_at
            count = len(self._flight_times)

        if idle < STATE_TYPING_SEC and count >= 3:
            return "typing"
        elif idle < STATE_READING_SEC:
            return "reading"
        else:
            return "thinking"
