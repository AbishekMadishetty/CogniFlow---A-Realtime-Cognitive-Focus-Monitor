"""
CogniFlow — Mouse Sensor
Tracks mouse movement and clicks to detect active engagement.
Never records screen position or what was clicked.
"""

import time
import math
import threading
from pynput import mouse


MIN_MOVE_DISTANCE  = 5     # pixels — ignore micro tremors
ACTIVE_TIMEOUT_SEC = 10    # inactive after this many seconds


class MouseSensor:

    def __init__(self):
        self._lock         = threading.Lock()
        self._last_move_at = 0.0
        self._last_pos     = (0, 0)
        self._listener     = None

    def start(self):
        self._listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self._listener.daemon = True
        self._listener.start()
        print("[Mouse] Listener started.")

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_move(self, x, y):
        dist = math.dist((x, y), self._last_pos)
        if dist >= MIN_MOVE_DISTANCE:
            with self._lock:
                self._last_move_at = time.time()
                self._last_pos     = (x, y)

    def _on_click(self, x, y, button, pressed):
        if pressed:
            with self._lock:
                self._last_move_at = time.time()

    def _on_scroll(self, x, y, dx, dy):
        with self._lock:
            self._last_move_at = time.time()

    def is_active(self):
        with self._lock:
            if self._last_move_at == 0:
                return False
            return (time.time() - self._last_move_at) < ACTIVE_TIMEOUT_SEC
