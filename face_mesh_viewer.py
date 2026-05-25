"""
CogniFlow — Face Mesh Viewer
Reads shared frames from WebcamSensor — no second camera opened.
Stops cleanly via shutdown_event.
"""

import cv2
import math
import time

COLOR_GREEN  = (0,   220,  80)
COLOR_YELLOW = (0,   200, 255)
COLOR_RED    = (0,    50, 220)
COLOR_WHITE  = (255, 255, 255)
COLOR_GRAY   = (160, 160, 160)
COLOR_CYAN   = (255, 200,   0)
COLOR_ORANGE = (0,   140, 255)

LEFT_EYE    = [362, 385, 387, 263, 373, 380]
RIGHT_EYE   = [33,  160, 158, 133, 153, 144]
MOUTH_TOP   = 13
MOUTH_BOT   = 14
MOUTH_LEFT  = 78
MOUTH_RIGHT = 308
LEFT_IRIS   = [474, 475, 476, 477]
RIGHT_IRIS  = [469, 470, 471, 472]

LIPS_OUTLINE = [
    61, 185, 40, 39, 37, 0, 267, 269, 270, 409,
    291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61
]
JAWLINE = [
    10, 338, 297, 332, 284, 251, 389, 356, 454,
    323, 361, 288, 397, 365, 379, 378, 400, 377,
    152, 148, 176, 149, 150, 136, 172, 58, 132,
    93, 234, 127, 162, 21, 54, 103, 67, 109, 10
]


class FaceMeshViewer:

    def __init__(self, webcam_sensor, engine, shutdown_event):
        self.sensor         = webcam_sensor
        self.engine         = engine
        self.shutdown_event = shutdown_event

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _ear(self, lm, idx):
        v = math.dist([lm[idx[1]].x, lm[idx[1]].y],
                      [lm[idx[5]].x, lm[idx[5]].y])
        h = math.dist([lm[idx[0]].x, lm[idx[0]].y],
                      [lm[idx[3]].x, lm[idx[3]].y])
        return v / h if h else 0.0

    def _mar(self, lm):
        v = math.dist([lm[MOUTH_TOP].x, lm[MOUTH_TOP].y],
                      [lm[MOUTH_BOT].x, lm[MOUTH_BOT].y])
        h = math.dist([lm[MOUTH_LEFT].x, lm[MOUTH_LEFT].y],
                      [lm[MOUTH_RIGHT].x, lm[MOUTH_RIGHT].y])
        return v / h if h else 0.0

    def _px(self, lm, idx, w, h):
        return int(lm[idx].x * w), int(lm[idx].y * h)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw_eye(self, frame, lm, idx, w, h, color):
        pts = [self._px(lm, i, w, h) for i in idx]
        for i in range(len(pts)):
            cv2.line(frame, pts[i], pts[(i + 1) % len(pts)],
                     color, 1, cv2.LINE_AA)

    def _draw_iris(self, frame, lm, idx, w, h):
        pts = [self._px(lm, i, w, h) for i in idx]
        cx  = sum(p[0] for p in pts) // len(pts)
        cy  = sum(p[1] for p in pts) // len(pts)
        r   = int(math.dist(pts[0], pts[2]) / 2)
        cv2.circle(frame, (cx, cy), r, COLOR_CYAN, 1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 2, COLOR_CYAN, -1)

    def _draw_lips(self, frame, lm, w, h, color):
        pts = [self._px(lm, i, w, h) for i in LIPS_OUTLINE]
        for i in range(len(pts) - 1):
            cv2.line(frame, pts[i], pts[i + 1], color, 1, cv2.LINE_AA)

    def _draw_jawline(self, frame, lm, w, h):
        pts = [self._px(lm, i, w, h) for i in JAWLINE]
        for i in range(len(pts) - 1):
            cv2.line(frame, pts[i], pts[i + 1], (70, 70, 70), 1, cv2.LINE_AA)

    def _draw_mesh_dots(self, frame, lm, w, h):
        for i in range(min(468, len(lm))):
            x, y = self._px(lm, i, w, h)
            cv2.circle(frame, (x, y), 1, (45, 45, 45), -1)

    # ── HUD panel ─────────────────────────────────────────────────────────────

    def _draw_hud(self, frame, ear, mar, thresholds, calibrated):
        fh, fw = frame.shape[:2]
        px     = fw - 215
        bar_w  = 175

        overlay = frame.copy()
        cv2.rectangle(overlay, (px - 10, 0), (fw, fh), (18, 18, 18), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        def txt(text, y, color=COLOR_WHITE, scale=0.52, bold=False):
            cv2.putText(frame, text, (px, y),
                        cv2.FONT_HERSHEY_SIMPLEX, scale,
                        color, 2 if bold else 1, cv2.LINE_AA)

        def bar(val, max_val, thr_val, y, color):
            filled = int(min(val / max_val, 1.0) * bar_w)
            cv2.rectangle(frame, (px, y), (px + bar_w, y + 7),
                          (55, 55, 55), -1)
            cv2.rectangle(frame, (px, y), (px + filled, y + 7), color, -1)
            thr_x = px + int((thr_val / max_val) * bar_w)
            cv2.line(frame, (thr_x, y - 2), (thr_x, y + 9), COLOR_RED, 2)

        def divider(y):
            cv2.line(frame, (px - 10, y), (fw, y), (55, 55, 55), 1)

        y = 28
        txt("CogniFlow", y, COLOR_GREEN, 0.62, bold=True)
        y += 28
        divider(y)
        y += 13

        if not calibrated:
            txt("Calibrating...", y, COLOR_YELLOW)
            y += 22
            txt("Sit normally,",  y, COLOR_GRAY, 0.44)
            y += 18
            txt("look at screen", y, COLOR_GRAY, 0.44)
            return

        if self.sensor.is_cam_blocked():
            txt("CAM BLOCKED!", y, COLOR_RED, 0.62, bold=True)
            return

        # EAR
        txt("EYE OPENNESS", y, COLOR_GRAY, 0.43)
        y += 17
        ear_base = thresholds.get("ear_baseline", 0.30)
        ear_thr  = thresholds.get("ear_closed",   0.20)
        ear_col  = COLOR_GREEN if ear >= ear_base * 0.85 else COLOR_RED
        txt(f"  EAR: {ear:.3f}", y, ear_col, 0.58, bold=True)
        y += 18
        txt(f"  Close thr: {ear_thr:.3f}", y, COLOR_GRAY, 0.40)
        y += 20
        bar(ear, ear_base * 1.2, ear_thr, y, ear_col)
        y += 18
        divider(y)
        y += 13

        # MAR
        txt("MOUTH OPENNESS", y, COLOR_GRAY, 0.43)
        y += 17
        yawn_thr = thresholds.get("yawn_threshold", 0.55)
        mar_col  = (COLOR_RED    if mar > yawn_thr else
                    COLOR_ORANGE if mar > yawn_thr * 0.75 else COLOR_GREEN)
        txt(f"  MAR: {mar:.3f}", y, mar_col, 0.58, bold=True)
        y += 18
        txt(f"  Yawn thr:  {yawn_thr:.3f}", y, COLOR_GRAY, 0.40)
        y += 20
        bar(mar, yawn_thr * 1.5, yawn_thr, y, mar_col)
        y += 18
        divider(y)
        y += 13

        # Focus score
        score = self.engine.current_score
        label = self.engine.current_label
        color = self.engine.current_color

        def hex_to_bgr(hx):
            hx = hx.lstrip("#")
            r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
            return (b, g, r)

        txt("FOCUS SCORE", y, COLOR_GRAY, 0.43)
        y += 17
        txt(f"  {score}/100  {label}", y, hex_to_bgr(color), 0.58, bold=True)
        y += 20
        filled = int((score / 100) * bar_w)
        cv2.rectangle(frame, (px, y), (px + bar_w, y + 7), (55, 55, 55), -1)
        cv2.rectangle(frame, (px, y), (px + filled, y + 7), hex_to_bgr(color), -1)
        y += 18
        divider(y)
        y += 13

        # State
        state = self.engine.current_state
        state_colors = {
            "typing":   COLOR_GREEN,
            "reading":  COLOR_CYAN,
            "thinking": COLOR_YELLOW
        }
        txt("STATE", y, COLOR_GRAY, 0.43)
        y += 17
        txt(f"  {state.upper()}", y,
            state_colors.get(state, COLOR_WHITE), 0.58, bold=True)
        y += 20
        divider(y)
        y += 13

        # Session counts
        txt("SESSION", y, COLOR_GRAY, 0.43)
        y += 17
        yawns  = self.sensor.get_yawn_count()
        closes = self.sensor.get_eye_close_count()
        txt(f"  Yawns:      {yawns}", y,
            COLOR_RED if yawns  >= 3 else COLOR_WHITE)
        y += 18
        txt(f"  Eye closes: {closes}", y,
            COLOR_RED if closes >= 3 else COLOR_WHITE)
        y += 20
        divider(y)
        y += 13

        # Activity
        activity  = self.engine.current_activity
        act_short = activity[:24] + "..." if len(activity) > 24 else activity
        txt("ACTIVITY", y, COLOR_GRAY, 0.43)
        y += 17
        txt(f"  {act_short}", y, COLOR_CYAN, 0.42)
        y += 20
        divider(y)
        y += 13

        # Clock
        txt(time.strftime("%H:%M:%S"), y, COLOR_GRAY, 0.48)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def start(self):
        self._loop()

    def _loop(self):
        print("[FaceMesh] Viewer started — reading shared frames.")

        while not self.shutdown_event.is_set():
            frame, lm = self.sensor.get_latest_frame()

            if frame is None:
                time.sleep(0.03)
                continue

            frame  = cv2.flip(frame, 1)
            fh, fw = frame.shape[:2]

            calibrated = self.sensor.is_calibrated()
            thresholds = self.sensor.get_thresholds() if calibrated else {}
            ear, mar   = 0.0, 0.0

            if lm is not None:
                # Mirror landmarks to match flipped frame
                class M:
                    def __init__(self, p):
                        self.x = 1.0 - p.x
                        self.y = p.y
                        self.z = p.z

                mlm = [M(p) for p in lm]

                ear = (self._ear(mlm, LEFT_EYE) +
                       self._ear(mlm, RIGHT_EYE)) / 2.0
                mar = self._mar(mlm)

                ear_thr  = thresholds.get("ear_closed",    0.20)
                yawn_thr = thresholds.get("yawn_threshold", 0.55)

                self._draw_mesh_dots(frame, mlm, fw, fh)
                self._draw_jawline(frame, mlm, fw, fh)

                eye_col = COLOR_RED if ear < ear_thr else COLOR_GREEN
                self._draw_eye(frame, mlm, LEFT_EYE,  fw, fh, eye_col)
                self._draw_eye(frame, mlm, RIGHT_EYE, fw, fh, eye_col)
                self._draw_iris(frame, mlm, LEFT_IRIS,  fw, fh)
                self._draw_iris(frame, mlm, RIGHT_IRIS, fw, fh)

                lip_col = (COLOR_RED    if mar > yawn_thr else
                           COLOR_ORANGE if mar > yawn_thr * 0.75
                           else COLOR_GREEN)
                self._draw_lips(frame, mlm, fw, fh, lip_col)

            else:
                msg = ("CAMERA BLOCKED" if self.sensor.is_cam_blocked()
                       else "No face detected")
                col = COLOR_RED if self.sensor.is_cam_blocked() else COLOR_GRAY
                cv2.putText(frame, msg, (fw // 2 - 120, fh // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2,
                            cv2.LINE_AA)

            self._draw_hud(frame, ear, mar, thresholds, calibrated)
            self.current_frame = frame.copy()
            cv2.imshow("CogniFlow — Face Mesh", frame)

            # Q or window close triggers full shutdown
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.shutdown_event.set()
                break

            # Handle window X button
            try:
                if cv2.getWindowProperty(
                        "CogniFlow — Face Mesh",
                        cv2.WND_PROP_VISIBLE) < 1:
                    self.shutdown_event.set()
                    break
            except Exception:
                pass

        cv2.destroyAllWindows()
        print("[FaceMesh] Viewer stopped.")
