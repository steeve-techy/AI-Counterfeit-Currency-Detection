import cv2
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from ultralytics import RTDETR

# --- CONFIGURATION ---
LOCAL_MODEL = 'best.pt'
CONF_THRESH = 0.50 
CAMERA_PORT = 1

# --- MANUAL STATE MACHINE WITH TELEMETRY ---
system_state = {
    "active_mode": "VISUAL", 
    "status": "SYSTEM READY: AWAITING VISUAL LOCK",
    "note_detected": "None",
    "raw_detection": "NO TARGET (0%)", # NEW: Live telemetry string
    "visual_pass": False,
    "uv_pass": False,
    "watermark_pass": False,
    "genuine": False
}

app = FastAPI()

print(">>> INITIALIZING RT-DETR CLASSIFICATION CORE...")
try:
    model = RTDETR(LOCAL_MODEL)
    print(">>> AI ONLINE. MANUAL OVERRIDE ENGAGED.")
except Exception as e:
    print(f"!!! FATAL AI BOOT ERROR: {e}")
    exit()

cap = cv2.VideoCapture(CAMERA_PORT, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

def generate_frames():
    global system_state
    
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        h, w = frame.shape[:2]
        crop_sz = min(h, w)
        cx, cy = w//2, h//2
        x1, y1 = cx - crop_sz//2, cy - crop_sz//2
        ai_crop = frame[y1:y1+crop_sz, x1:x1+crop_sz]
        
        box_color = (100, 100, 100) # Default Gray
        if system_state["active_mode"] == "VISUAL": box_color = (0, 165, 255) 
        if system_state["active_mode"] == "UV": box_color = (255, 255, 0) 
        if system_state["active_mode"] == "WATERMARK": box_color = (255, 100, 100) 
        if system_state["genuine"]: box_color = (0, 255, 0) 
        
        raw_text = "SENSOR: NO TARGET"
        
        try:
            results = model.predict(ai_crop, imgsz=640, verbose=False)
            boxes = results[0].boxes
            
            if len(boxes) > 0:
                best_box = boxes[0]
                conf = best_box.conf.item()
                label = model.names[int(best_box.cls.item())]
                
                # --- LIVE TELEMETRY OVERRIDE (Always runs) ---
                raw_text = f"SENSOR: {label.upper()} ({int(conf * 100)}%)"
                system_state["raw_detection"] = raw_text
                
                # --- MODE 1: VISUAL SCAN ---
                if system_state["active_mode"] == "VISUAL" and "real" in label and conf > CONF_THRESH:
                    if not system_state["visual_pass"]:
                        system_state["note_detected"] = label.split('_')[0] + " INR"
                        system_state["visual_pass"] = True
                        system_state["status"] = f"LOCKED: {system_state['note_detected']}. SWITCH TO UV."
                
                # --- MODE 2: UV SCAN ---
                elif system_state["active_mode"] == "UV" and label == "uv_glowing" and conf > 0.65:
                    if not system_state["uv_pass"]:
                        system_state["uv_pass"] = True
                        system_state["status"] = "UV VERIFIED. SWITCH TO WATERMARK."
                    
                # --- MODE 3: WATERMARK SCAN ---
                elif system_state["active_mode"] == "WATERMARK" and label == "watermark" and conf > 0.70:
                    if not system_state["watermark_pass"]:
                        system_state["watermark_pass"] = True
                        system_state["status"] = "WATERMARK VERIFIED."
                
                # --- FINAL CHECK ---
                if system_state["visual_pass"] and system_state["uv_pass"] and system_state["watermark_pass"]:
                    system_state["genuine"] = True
                    system_state["status"] = f"GENUINE {system_state['note_detected']} VERIFIED."
            else:
                system_state["raw_detection"] = "SENSOR: NO TARGET (0%)"
                        
        except Exception as e:
            pass 

        # Draw Telemetry directly onto the video feed (Top Left)
        cv2.putText(frame, raw_text, (20, 40), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 217), 2)

        # Draw HUD brackets
        l = 40
        cv2.line(frame, (x1, y1), (x1+l, y1), box_color, 4)
        cv2.line(frame, (x1, y1), (x1, y1+l), box_color, 4)
        cv2.line(frame, (x1+crop_sz, y1+crop_sz), (x1+crop_sz-l, y1+crop_sz), box_color, 4)
        cv2.line(frame, (x1+crop_sz, y1+crop_sz), (x1+crop_sz, y1+crop_sz-l), box_color, 4)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# --- API ENDPOINTS ---

@app.get("/status")
async def get_status():
    return system_state

@app.post("/set_mode/{mode}")
async def set_mode(mode: str):
    global system_state
    if mode in ["VISUAL", "UV", "WATERMARK"]:
        system_state["active_mode"] = mode
        system_state["status"] = f"MANUAL OVERRIDE: SCANNING {mode}"
    return system_state

@app.post("/reset")
async def reset_system():
    global system_state
    system_state = {
        "active_mode": "VISUAL",
        "status": "SYSTEM READY: AWAITING VISUAL LOCK",
        "note_detected": "None",
        "raw_detection": "SENSOR: NO TARGET (0%)",
        "visual_pass": False,
        "uv_pass": False,
        "watermark_pass": False,
        "genuine": False
    }
    return system_state

@app.get("/")
async def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Counterfeit Detection Matrix</title>
        <style>
            :root { --bg-color: #0f111a; --panel-bg: #1a1d2d; --text-main: #e2e8f0; --accent-cyan: #00ffd9; --accent-green: #10b981; --accent-red: #ef4444; --accent-orange: #f59e0b; }
            body { background-color: var(--bg-color); color: var(--text-main); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; height: 100vh; box-sizing: border-box; }
            header { padding-bottom: 20px; border-bottom: 1px solid #2d3748; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;}
            header h1 { margin: 0; font-size: 1.5rem; color: var(--accent-cyan); text-transform: uppercase; }
            
            .controls { display: flex; gap: 10px; }
            button { background-color: #2d3748; color: white; border: 1px solid #4a5568; padding: 10px 15px; border-radius: 4px; font-weight: bold; cursor: pointer; text-transform: uppercase; transition: 0.2s;}
            button:hover { background-color: #4a5568; }
            .btn-reset { background-color: rgba(239, 68, 68, 0.2); border-color: var(--accent-red); color: var(--accent-red); }
            .btn-reset:hover { background-color: var(--accent-red); color: white;}
            .btn-active { background-color: var(--accent-cyan); color: #000; border-color: var(--accent-cyan); }

            .dashboard-container { display: flex; gap: 20px; flex: 1; min-height: 0; }
            .video-section { flex: 3; background-color: var(--panel-bg); border: 1px solid #2d3748; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center;}
            .video-section img { width: 100%; height: 100%; object-fit: contain; }
            .sidebar { flex: 1; display: flex; flex-direction: column; gap: 20px; }
            .card { background-color: var(--panel-bg); border: 1px solid #2d3748; border-radius: 8px; padding: 20px; }
            .card h2 { margin-top: 0; font-size: 1.1rem; color: #a0aec0; border-bottom: 1px solid #2d3748; padding-bottom: 10px; }
            
            .telemetry-box { font-family: monospace; font-size: 1.1rem; color: var(--accent-cyan); background: #000; padding: 10px; border-radius: 4px; border: 1px solid #333; margin-bottom: 15px; text-align: center; letter-spacing: 1px;}
            
            .status-indicator { font-size: 1.1rem; font-weight: bold; text-align: center; padding: 15px; border-radius: 4px; background: #2d3748; color: white; border: 1px solid #4a5568; transition: all 0.3s; }
            .checklist-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #2d3748; }
            .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; background: #4a5568; color: white; transition: all 0.3s;}
            .badge-pass { background-color: rgba(16, 185, 129, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }
            .status-genuine { background-color: rgba(16, 185, 129, 0.1); color: var(--accent-green); border-color: var(--accent-green); }
        </style>
    </head>
    <body>
        <header>
            <h1>Production HUD // Edge Verifier</h1>
            <div class="controls">
                <button id="btn-VISUAL" onclick="setMode('VISUAL')">1. BASE NOTE</button>
                <button id="btn-UV" onclick="setMode('UV')">2. UV LIGHT</button>
                <button id="btn-WATERMARK" onclick="setMode('WATERMARK')">3. WATERMARK</button>
                <button class="btn-reset" onclick="resetSystem()">RESET SCAN</button>
            </div>
        </header>

        <div class="dashboard-container">
            <div class="video-section">
                <img src="/video_feed" alt="Camera Feed Offline" />
            </div>

            <div class="sidebar">
                <div class="card">
                    <h2>LIVE AI TELEMETRY</h2>
                    <div id="telemetry-feed" class="telemetry-box">SENSOR: BOOTING...</div>
                </div>
                
                <div class="card">
                    <h2>SYSTEM LOGIC</h2>
                    <div id="main-status" class="status-indicator">BOOTING...</div>
                    <div style="text-align: center; margin-top: 10px; color: #a0aec0; font-size: 0.9rem;">
                        Target Lock: <span id="note-type" style="color: white; font-weight: bold;">None</span>
                    </div>
                </div>

                <div class="card">
                    <h2>VERIFICATION LEDGER</h2>
                    <div class="checklist-item">
                        <span>1. Base Visual ID</span>
                        <span id="badge-visual" class="badge">PENDING</span>
                    </div>
                    <div class="checklist-item">
                        <span>2. UV Fluorescence</span>
                        <span id="badge-uv" class="badge">PENDING</span>
                    </div>
                    <div class="checklist-item">
                        <span>3. Watermark Density</span>
                        <span id="badge-watermark" class="badge">PENDING</span>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function setMode(mode) {
                await fetch(`/set_mode/${mode}`, { method: 'POST' });
            }

            async function resetSystem() {
                await fetch('/reset', { method: 'POST' });
            }

            async function updateDashboard() {
                try {
                    const response = await fetch('/status');
                    const data = await response.json();
                    
                    // Update Telemetry
                    document.getElementById('telemetry-feed').innerText = data.raw_detection;
                    
                    // Update Status Text
                    const statusEl = document.getElementById('main-status');
                    statusEl.innerText = data.status;
                    document.getElementById('note-type').innerText = data.note_detected;

                    statusEl.className = 'status-indicator'; 
                    if (data.genuine) statusEl.classList.add('status-genuine');

                    // Update Top Buttons
                    document.getElementById('btn-VISUAL').className = data.active_mode === 'VISUAL' ? 'btn-active' : '';
                    document.getElementById('btn-UV').className = data.active_mode === 'UV' ? 'btn-active' : '';
                    document.getElementById('btn-WATERMARK').className = data.active_mode === 'WATERMARK' ? 'btn-active' : '';

                    // Update Ledger Badges
                    const visBadge = document.getElementById('badge-visual');
                    visBadge.innerText = data.visual_pass ? "VERIFIED" : "PENDING";
                    visBadge.className = data.visual_pass ? "badge badge-pass" : "badge";

                    const uvBadge = document.getElementById('badge-uv');
                    uvBadge.innerText = data.uv_pass ? "VERIFIED" : "PENDING";
                    uvBadge.className = data.uv_pass ? "badge badge-pass" : "badge";

                    const wmBadge = document.getElementById('badge-watermark');
                    wmBadge.innerText = data.watermark_pass ? "VERIFIED" : "PENDING";
                    wmBadge.className = data.watermark_pass ? "badge badge-pass" : "badge";

                } catch (error) {
                    console.error("Connection lost to backend.");
                }
            }
            setInterval(updateDashboard, 200);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    print(">>> SERVERS IGNITED. ACCESS DASHBOARD AT http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)