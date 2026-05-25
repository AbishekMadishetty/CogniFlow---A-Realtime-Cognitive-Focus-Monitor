"""
CogniFlow — Entry Point
Tkinter owns the main thread. Clean shutdown via shared threading.Event.
Now includes Cloud Telemetry Sync and Web Video Streaming.
"""

import threading
import tkinter as tk
import sys
import subprocess
import time
import requests
import cv2
import csv
import os
from datetime import datetime
from flask import Flask, Response 

from engine import CogniFlowEngine
from tray import TrayApp
from face_mesh_viewer import FaceMeshViewer

# ==========================================
# 1. CLOUD TELEMETRY SYNC
# ==========================================
API_URL = "http://localhost:8000/api/telemetry"

def cloud_sync_loop(engine, shutdown_event):
    """Runs in the background, grabbing engine stats, posting to Docker, and saving to a Session CSV."""
    
    # --- SESSION INITIALIZATION LOGIC ---
    csv_file = "cogniflow_master_log.csv"
    session_id = 1
    
    # Check if the file exists to figure out the next Session ID
    if os.path.exists(csv_file):
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > 1: # Ensure it has more than just headers
                try:
                    # Grab the very last line, split by comma, get the first column (Session ID)
                    last_session = int(lines[-1].split(',')[0])
                    session_id = last_session + 1
                except ValueError:
                    pass
    else:
        # If it's the very first time running, create the file and add headers
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Session_ID", "Timestamp", "Focus_Score", "User_State", "Activity_Context", "Total_Yawns", "Eye_Closures", "ML_Prediction"])
    
    print(f"\n[*] STARTED LOCAL DATALOGGING: Session {session_id} initialized.")
    # ------------------------------------

    while not shutdown_event.is_set():
        time.sleep(2.0)
        try:
            # 1. Grab the latest data exactly matching your engine variables
            payload = {
                "score": int(engine.current_score),
                "state": str(engine.current_state) if hasattr(engine, 'current_state') else "tracking",
                "activity": str(engine.current_app) if hasattr(engine, 'current_app') else "System",
                "yawns": int(engine.total_yawns),
                "eye_closes": int(engine.total_eye_closes),
                "ml_label": str(engine.ml_label) if hasattr(engine, 'ml_label') else "focused"
            }
            
            # 2. WRITE TO LOCAL CSV (The new step)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    session_id, 
                    current_time, 
                    payload["score"], 
                    payload["state"], 
                    payload["activity"], 
                    payload["yawns"], 
                    payload["eye_closes"], 
                    payload["ml_label"]
                ])

            # 3. POST to Docker Dashboard
            requests.post(API_URL, json=payload, timeout=1)
            
        except Exception:
            pass # Fail silently if backend is offline so the edge engine runs smoothly
# ==========================================
# 2. FLASK VIDEO SERVER
# ==========================================
app = Flask(__name__)
global_viewer = None # Reference to grab frames from your viewer

def generate_video():
    """Generator that safely asks your FaceMeshViewer for its latest frame and crops it."""
    global global_viewer
    while True:
        if global_viewer and hasattr(global_viewer, 'current_frame') and global_viewer.current_frame is not None:
            # Grab the frame from the viewer
            frame = global_viewer.current_frame.copy()
            
           # --- THE CROP FIX ---
            h, w, channels = frame.shape
            # If the frame is wider than a standard webcam (meaning the sidebar is attached)
            if w > 640:  
                # Hard-crop to exactly 640 pixels wide (pure webcam, zero sidebar)
                clean_face_frame = frame[:, :640]
            else:
                clean_face_frame = frame
            # --------------------

            flag, encodedImage = cv2.imencode(".jpg", clean_face_frame)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        
        time.sleep(0.03) # Cap at ~30 FPS to save CPU

@app.route("/video_feed")
def video_feed():
    return Response(generate_video(), mimetype="multipart/x-mixed-replace; boundary=frame")

def start_video_server():
    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)

# ==========================================
# 3. MAIN ORCHESTRATOR
# ==========================================
def main():
    global global_viewer
    print("=" * 50)
    print("  CogniFlow — Starting up...")
    print("=" * 50)

    shutdown_event = threading.Event()

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", False)

    # Initialize your modular components
    engine = CogniFlowEngine(shutdown_event)
    tray   = TrayApp(engine, root, shutdown_event)
    viewer = FaceMeshViewer(engine.webcam, engine, shutdown_event)
    
    global_viewer = viewer # Give Flask access to the viewer

    # Start original threads
    threading.Thread(target=engine.run,   daemon=True).start()
    threading.Thread(target=viewer.start, daemon=True).start()
    threading.Thread(target=tray.start,   daemon=True).start()

    # --- NEW: Start Cloud Threads ---
    threading.Thread(target=cloud_sync_loop, args=(engine, shutdown_event), daemon=True).start()
    threading.Thread(target=start_video_server, daemon=True).start()

    # You can comment this out if you don't want the old local dashboard popping up anymore!
    # subprocess.Popen([sys.executable, "dashboard.py"])

    def check_shutdown():
        if shutdown_event.is_set():
            root.quit()
        else:
            root.after(300, check_shutdown)

    root.after(300, check_shutdown)
    root.mainloop()

    print("[CogniFlow] Fully stopped.")
    sys.exit(0)

if __name__ == "__main__":
    main()