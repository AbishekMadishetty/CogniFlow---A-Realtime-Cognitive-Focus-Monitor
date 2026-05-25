# CogniFlow---A-Realtime-Cognitive-Focus-Monitor
This desktop application uses Python, MediaPipe, and machine learning to track real-time cognitive focus and fatigue. By monitoring webcam feeds, keyboard activity, mouse movements, and active windows, it calculates a live Focus Score from 0 to 100 and alerts users when fatigue is detected.

---

## Requirements
- Windows 10 or 11
- Python 3.10 or 3.11 (NOT 3.12 — mediapipe doesn't support it yet)
- A working webcam

---

## Setup (do this once)

### Step 1 — Create a virtual environment
```
python -m venv cogniflow_env
cogniflow_env\Scripts\activate
```

### Step 2 — Install dependencies
```
pip install -r requirements.txt
```

---

## Running CogniFlow

```
python main.py
```

---

## What happens when you run it

1. A Face Mesh Viewer window opens showing your live face with landmarks
2. A CogniFlow icon appears in the system tray (bottom right of taskbar)
3. For the first 30 seconds it calibrates to YOUR personal baseline
4. After calibration, Focus Score starts updating every 2 seconds
5. Alerts pop up in the bottom right corner when you're fatigued

---

## Face Mesh Viewer

| Color | Meaning |
|-------|---------|
| Green eyes | Eyes open — healthy |
| Red eyes | Eyes closed — fatigue detected |
| Green lips | Mouth closed — normal |
| Orange lips | Mouth slightly open |
| Red lips | Yawning detected |

Press **Q** to close the viewer (also shuts down the whole app).
Close the window X button also shuts everything down cleanly.

---

## System Tray Icon

Right-click the tray icon for:
- **Show Status** — current score, state, yawns, activity
- **Session Summary** — full session stats
- **Quit CogniFlow** — clean shutdown

Icon colors:
- 🟢 Green = Deep Focus / Focused (75-100)
- 🟡 Yellow = Moderate (50-74)
- 🟠 Orange = Drifting / Fatigued (30-49)
- 🔴 Red = Exhausted (0-29)

---

## Focus Score Labels

| Score | Label |
|-------|-------|
| 85-100 | Deep Focus |
| 70-84 | Focused |
| 55-69 | Moderate |
| 40-54 | Drifting |
| 25-39 | Fatigued |
| 0-24 | Exhausted |

---

## Alert Sounds

| Alert | Sound |
|-------|-------|
| Low focus | 3 descending beeps |
| Camera blocked | 3 sharp beeps + low tone |
| Eyes closed | 3 slow descending tones |
| Too many yawns | C-E-G musical chord |
| Info | 2 ascending beeps |

---

## Session Data

All session data is saved to `cogniflow_log.csv` in the same folder.
Columns: Time, Score, Label, State, EAR, Variance, Yawns, EyeCloses, Activity

---

## File Structure

```
cogniflow/
├── main.py              # Entry point
├── engine.py            # Focus score engine
├── webcam_sensor.py     # EAR, MAR, yawn, eye close, blocking
├── keyboard_sensor.py   # Typing rhythm tracking
├── mouse_sensor.py      # Mouse activity tracking
├── window_sensor.py     # Active app + section detection
├── face_mesh_viewer.py  # OpenCV face mesh display
├── tray.py              # System tray icon + popups
├── alert_sound.py       # Alert sounds
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## Troubleshooting

**Camera not opening**
- Make sure no other app (Teams, Zoom, etc.) is using the camera
- Try changing `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` in webcam_sensor.py

**mediapipe install fails**
- Make sure you're using Python 3.10 or 3.11
- Run: `pip install mediapipe==0.10.14 --break-system-packages`

**Yawn false positives**
- Sit still during the 30 second calibration
- Keep your mouth closed during calibration
- Don't talk or smile during the first 30 seconds

**Score stuck at Calibrating**
- Make sure your face is visible to the camera
- Ensure good lighting — not too dark
- The calibration needs at least 10 EAR samples and 15 MAR samples
