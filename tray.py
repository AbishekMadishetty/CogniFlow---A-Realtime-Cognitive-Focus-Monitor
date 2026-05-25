"""
CogniFlow — System Tray App
Animated tray icon + styled popup notifications + alert sounds.
Popups scheduled on main Tkinter thread to avoid RuntimeError.
Clean shutdown via shared threading.Event.
"""

import threading
import time
import math
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item
import tkinter as tk
from tkinter import ttk
from alert_sound import play as play_sound
import subprocess
import sys


ICON_SIZE   = 64
PULSE_STEPS = 12


class TrayApp:

    def __init__(self, engine, tk_root, shutdown_event):
        self.engine         = engine
        self.root           = tk_root
        self.shutdown_event = shutdown_event
        self._icon          = None
        self._anim_frame    = 0

    # ── Icon generation ───────────────────────────────────────────────────────

    def _hex_to_rgb(self, h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _make_icon(self, score, color_hex, pulse_phase=0):
        size    = ICON_SIZE
        img     = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        r, g, b = self._hex_to_rgb(color_hex)
        cx, cy  = size // 2, size // 2

        # Pulse ring
        pulse_r    = 2 + int(math.sin(pulse_phase * math.pi / PULSE_STEPS) * 3)
        ring_alpha = int(180 + math.sin(pulse_phase * math.pi / PULSE_STEPS) * 75)
        ring_img   = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ring_draw  = ImageDraw.Draw(ring_img)
        ring_draw.ellipse(
            [cx - 30 - pulse_r, cy - 30 - pulse_r,
             cx + 30 + pulse_r, cy + 30 + pulse_r],
            outline=(r, g, b, ring_alpha), width=2
        )
        img  = Image.alpha_composite(img, ring_img)
        draw = ImageDraw.Draw(img)

        # Arc track + filled arc
        draw.ellipse([4, 4, size - 4, size - 4],
                     outline=(60, 60, 60, 180), width=4)
        if score > 0:
            draw.arc([4, 4, size - 4, size - 4],
                     start=-90, end=-90 + int((score / 100) * 360),
                     fill=(r, g, b, 255), width=4)

        # Inner circle
        draw.ellipse([10, 10, size - 10, size - 10], fill=(r, g, b, 230))

        # Score text
        try:
            font = ImageFont.truetype("arialbd.ttf", 19)
        except Exception:
            try:    font = ImageFont.truetype("arial.ttf", 18)
            except: font = ImageFont.load_default()

        text = str(score)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2 - 1),
                  text, fill=(255, 255, 255, 255), font=font)
        return img

    def _make_blocked_icon(self):
        size = ICON_SIZE
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, size - 4, size - 4], fill=(180, 20, 20, 230))
        p = 18
        draw.line([p, p, size - p, size - p], fill=(255, 255, 255), width=3)
        draw.line([size - p, p, p, size - p], fill=(255, 255, 255), width=3)
        return img

    def _make_calibrating_icon(self, progress):
        size = ICON_SIZE
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, size - 8, size - 8], fill=(50, 50, 50, 200))
        if progress > 0:
            draw.arc([4, 4, size - 4, size - 4],
                     start=-90, end=-90 + int((progress / 100) * 360),
                     fill=(100, 180, 255, 255), width=5)
        try:    font = ImageFont.truetype("arial.ttf", 13)
        except: font = ImageFont.load_default()
        draw.text((size // 2 - 10, size // 2 - 8),
                  f"{progress}%", fill=(200, 200, 200), font=font)
        return img

    # ── Popup ─────────────────────────────────────────────────────────────────

    def _show_popup(self, title, message, color="#00C853", popup_type="info"):
        self.root.after(0, lambda: self._build_popup(
            title, message, color, popup_type))

    def _build_popup(self, title, message, color, popup_type):
        try:
            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            popup.attributes("-alpha", 0.0)
            popup.configure(bg="#1E1E1E")

            sw, sh = popup.winfo_screenwidth(), popup.winfo_screenheight()
            w, h   = 340, 145
            popup.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 60}")

            tk.Frame(popup, bg=color, height=6).pack(fill="x", side="top")

            icon_map = {"info": "🧠", "warning": "⚠️",
                        "blocked": "🚫", "sleep": "😴", "break": "☕"}
            title_frame = tk.Frame(popup, bg="#1E1E1E")
            title_frame.pack(fill="x", padx=12, pady=(8, 2))

            tk.Label(title_frame, text=icon_map.get(popup_type, "🧠"),
                     font=("Segoe UI Emoji", 15),
                     bg="#1E1E1E", fg="white").pack(side="left", padx=(0, 8))

            tk.Label(title_frame, text=title,
                     font=("Segoe UI", 11, "bold"),
                     bg="#1E1E1E", fg="white").pack(side="left")

            tk.Label(popup, text=message,
                     font=("Segoe UI", 9), bg="#1E1E1E", fg="#CCCCCC",
                     wraplength=305, justify="left"
                     ).pack(padx=16, pady=(4, 0), anchor="w")

            style = ttk.Style(popup)
            style.theme_use("clam")
            style.configure("Popup.Horizontal.TProgressbar",
                            troughcolor="#2A2A2A", background=color,
                            borderwidth=0, thickness=3)
            progress_var = tk.DoubleVar(value=100)
            ttk.Progressbar(popup, variable=progress_var,
                            style="Popup.Horizontal.TProgressbar",
                            maximum=100, length=w - 24
                            ).pack(padx=12, pady=(8, 0))

            tk.Button(popup, text="✕", font=("Segoe UI", 8),
                      bg="#1E1E1E", fg="#888888",
                      activebackground="#2A2A2A", activeforeground="white",
                      bd=0, cursor="hand2",
                      command=popup.destroy).place(x=w - 24, y=10)

            popup.configure(highlightbackground="#333333", highlightthickness=1)

            def fade_in(alpha=0.0):
                if not popup.winfo_exists(): return
                if alpha < 1.0:
                    popup.attributes("-alpha", min(alpha, 1.0))
                    popup.after(20, lambda: fade_in(alpha + 0.08))
                else:
                    popup.attributes("-alpha", 1.0)

            steps = 8000 // 50
            count = [0]

            def tick():
                if not popup.winfo_exists(): return
                count[0] += 1
                progress_var.set(max(0, 100 - (count[0] / steps) * 100))
                if count[0] >= steps: fade_out()
                else: popup.after(50, tick)

            def fade_out(alpha=1.0):
                if not popup.winfo_exists(): return
                if alpha > 0.0:
                    popup.attributes("-alpha", alpha)
                    popup.after(20, lambda: fade_out(round(alpha - 0.1, 1)))
                else:
                    popup.destroy()

            popup.after(50,  fade_in)
            popup.after(100, tick)

        except Exception as e:
            print(f"[Tray] Popup error: {e}")

    # ── Tray menu actions ─────────────────────────────────────────────────────

    def _on_status(self, icon, item):
        engine = self.engine
        score  = engine.current_score
        ptype  = ("info"    if score >= 70 else
                  "warning" if score >= 40 else "sleep")
        self._show_popup(
            title      = f"Focus Score: {score}/100",
            message    = (
                f"Status:    {engine.current_label}\n"
                f"State:     {engine.current_state.upper()}\n"
                f"Yawns:     {engine.total_yawns}\n"
                f"Activity:  {engine.current_activity}"
            ),
            color      = engine.current_color,
            popup_type = ptype
        )
        play_sound(ptype)

    def _on_summary(self, icon, item):
        s = self.engine.summary()
        if not s:
            self._show_popup("No Data Yet", "Session hasn't started yet.",
                             "#90A4AE", "info")
            play_sound("info")
            return
        self._show_popup(
            title   = "Session Summary",
            message = (
                f"Duration:  {s['duration_min']} min\n"
                f"Average:   {s['average']}/100\n"
                f"Peak:      {s['peak_score']}/100  at {s['peak_time']}\n"
                f"Lowest:    {s['low_score']}/100  at {s['low_time']}\n"
                f"Dominant:  {s['dominant'].upper()}"
            ),
            color      = "#448AFF",
            popup_type = "info"
        )
        play_sound("info")


    def _on_dashboard(self, icon, item):
        """Open dashboard in separate process."""
        try:
            subprocess.Popen([sys.executable, 'dashboard.py'])
        except Exception as e:
            print(f'[Tray] Dashboard error: {e}')

    def _on_quit(self, icon, item):
        print("[CogniFlow] Shutting down...")
        s = self.engine.summary()
        if s:
            print("\n" + "═" * 45)
            print("  SESSION SUMMARY")
            print("═" * 45)
            print(f"  Duration:  {s['duration_min']} min")
            print(f"  Average:   {s['average']}/100")
            print(f"  Peak:      {s['peak_score']}/100  at {s['peak_time']}")
            print(f"  Lowest:    {s['low_score']}/100  at {s['low_time']}")
            print(f"  Dominant:  {s['dominant'].upper()}")
            print("═" * 45)

        self.engine.webcam.stop()
        self.engine.keyboard.stop()
        self.engine.mouse.stop()
        self.shutdown_event.set()
        icon.stop()

    # ── Animation + update loop ───────────────────────────────────────────────

    def _update_loop(self):
        while not self.shutdown_event.is_set():
            try:
                engine = self.engine

                if not engine.is_calibrated:
                    prog = engine.calibration_progress()
                    img  = self._make_calibrating_icon(prog)
                    if self._icon:
                        self._icon.icon  = img
                        self._icon.title = f"CogniFlow — Calibrating {prog}%"

                elif engine.webcam.is_cam_blocked():
                    img = self._make_blocked_icon()
                    if self._icon:
                        self._icon.icon  = img
                        self._icon.title = "CogniFlow — Camera Blocked!"

                else:
                    score = engine.current_score
                    color = engine.current_color
                    label = engine.current_label
                    speed = 1 if score >= 50 else 2
                    self._anim_frame = (
                        (self._anim_frame + speed) % (PULSE_STEPS * 2)
                    )
                    phase = (self._anim_frame
                             if self._anim_frame < PULSE_STEPS
                             else PULSE_STEPS * 2 - self._anim_frame)
                    img = self._make_icon(score, color, pulse_phase=phase)
                    if self._icon:
                        self._icon.icon  = img
                        self._icon.title = f"CogniFlow — {score}/100  {label}"

                if engine.alert_message:
                    msg              = engine.alert_message
                    engine.alert_message = None
                    if "blocked" in msg.lower():
                        ptype, col, ttl = "blocked", "#D50000", "Camera Blocked!"
                    elif "eyes" in msg.lower() or "sleep" in msg.lower():
                        ptype, col, ttl = "sleep",   "#FF6D00", "Fatigue Detected"
                    elif "yawn" in msg.lower():
                        ptype, col, ttl = "break",   "#FF6D00", "Break Reminder"
                    else:
                        ptype, col, ttl = "warning", "#FFD600", "Focus Alert"
                    self._show_popup(ttl, msg, col, ptype)
                    play_sound(ptype)

            except Exception:
                pass

            time.sleep(0.08)

    # ── Start ─────────────────────────────────────────────────────────────────

    def start(self):
        init_img = self._make_calibrating_icon(0)
        menu = pystray.Menu(
            item("Show Status",      self._on_status),
            item("Session Summary",  self._on_summary),
            item("Open Dashboard",   self._on_dashboard),
            pystray.Menu.SEPARATOR,
            item("Quit CogniFlow",   self._on_quit),
        )
        self._icon = pystray.Icon(
            name  = "CogniFlow",
            icon  = init_img,
            title = "CogniFlow — Starting...",
            menu  = menu,
        )
        threading.Thread(target=self._update_loop, daemon=True).start()
        print("[Tray] System tray ready!")
        self._icon.run()
