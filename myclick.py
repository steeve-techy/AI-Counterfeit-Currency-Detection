import cv2
import os
import time
import uuid

# --- CONFIG ---
OUTPUT_DIR = "raw_downloads"
INTERVAL = 0.15  

CLASSES = [
    "10_real", "20_real", "50_real", "100_real", "200_real",
    "500_real", "uv_glowing", "watermark", "empty"
]

def ensure_dir(folder):
    path = os.path.join(OUTPUT_DIR, folder)
    os.makedirs(path, exist_ok=True)
    return path

def start_universal_capture():
    print(">>> WAKING UP CAMERA...")
    
    # Brute-force port scanner to bypass Windows MSMF bullshit
    cap = None
    for port in [0, 1, 2]:
        print(f"[*] Trying camera port {port} with DirectShow...")
        temp_cap = cv2.VideoCapture(port, cv2.CAP_DSHOW)
        if temp_cap.isOpened():
            ret, _ = temp_cap.read()
            if ret:
                print(f"[+] SUCCESS! Locked onto port {port}")
                cap = temp_cap
                break
        temp_cap.release()

    if cap is None:
        print("!!! FATAL: Could not find a working camera on any port. Unplug it and plug it back in.")
        return

    class_idx = 0
    current_class = CLASSES[class_idx]
    
    is_recording = False
    last_shot = time.time()
    
    save_path = ensure_dir(current_class)
    count = len([name for name in os.listdir(save_path) if name.endswith('.jpg')])

    print("\n>>> UNIVERSAL RAPID FIRE READY")
    print("    [A] / [D]    Change Class")
    print("    [SPACE]      Start/Stop Recording")
    print("    [Q]          Quit\n")

    while True:
        ret, frame = cap.read()
        if not ret: 
            print("!!! FRAME DROP. Camera connection severed.")
            break

        display = frame.copy()
        h, w = display.shape[:2]
        
        # --- THE SQUARE CROP --- 
        crop_sz = min(h, w)
        cx, cy = w//2, h//2
        x1, y1 = cx - crop_sz//2, cy - crop_sz//2
        
        cv2.rectangle(display, (x1, y1), (x1+crop_sz, y1+crop_sz), (0, 255, 217), 2)

        # --- HUD ---
        cv2.rectangle(display, (0, 0), (w, 80), (0, 0, 0), -1)
        color = (0, 255, 0) if is_recording else (200, 200, 200)
        cv2.putText(display, f"TARGET: {current_class.upper()}", (30, 50), cv2.FONT_HERSHEY_DUPLEX, 1.0, color, 2)
        cv2.putText(display, f"COUNT: {count}", (w - 250, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        if is_recording:
            cv2.circle(display, (w - 50, 40), 15, (0, 0, 255), -1)
            cv2.putText(display, "REC", (w - 85, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        cv2.putText(display, "[A] PREV   [D] NEXT   [SPACE] CAPTURE", (30, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.imshow("Universal Capture Tool", display)
        
        # --- LOGIC ---
        if is_recording:
            if time.time() - last_shot > INTERVAL:
                filename = f"{current_class}_{uuid.uuid4().hex[:8]}.jpg"
                full_path = os.path.join(OUTPUT_DIR, current_class, filename)
                
                # Save crop
                ai_crop = frame[y1:y1+crop_sz, x1:x1+crop_sz]
                cv2.imwrite(full_path, ai_crop)
                
                count += 1
                last_shot = time.time()
                
                cv2.rectangle(display, (x1, y1), (x1+crop_sz, y1+crop_sz), (255, 255, 255), -1)
                cv2.imshow("Universal Capture Tool", display)
                cv2.waitKey(1) 

        # --- CONTROLS ---
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
            
        elif key == ord('a'): 
            class_idx = (class_idx - 1) % len(CLASSES)
            current_class = CLASSES[class_idx]
            save_path = ensure_dir(current_class)
            count = len([name for name in os.listdir(save_path) if name.endswith('.jpg')])
            is_recording = False
            
        elif key == ord('d'): 
            class_idx = (class_idx + 1) % len(CLASSES)
            current_class = CLASSES[class_idx]
            save_path = ensure_dir(current_class)
            count = len([name for name in os.listdir(save_path) if name.endswith('.jpg')])
            is_recording = False
            
        elif key == 32: # SPACE
            is_recording = not is_recording

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_universal_capture()