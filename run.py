import cv2
import time
import numpy as np
from ultralytics import RTDETR

# --- CONFIGURATION ---
LOCAL_MODEL = 'best.pt'  # Make sure this is the NEW best.pt from run 2
CONF_THRESH = 0.40       # Dropped to 0.40 to stop the model from gatekeeping itself
STABILITY_FRAMES = 8     # Frames required to lock onto a note

# Colors (BGR)
C_ACCENT = (0, 255, 217)   
C_GREEN  = (0, 255, 0)     
C_ORANGE = (0, 165, 255)   
C_RED    = (0, 0, 255)     
C_WHITE  = (255, 255, 255)
C_BLACK  = (0, 0, 0)
C_GRAY   = (100, 100, 100)

class EdgeVerifier:
    def __init__(self):
        print(f">>> BOOTING OFFLINE VERIFICATION MATRIX...")
        
        try:
            self.local_model = RTDETR(LOCAL_MODEL)
            print(">>> RT-DETR CORE: ONLINE")
        except Exception as e:
            print(f"!!! FATAL AI ERROR: {e}")
            return

        # Brute-force port scanner to bypass Windows MSMF crashes
        self.cap = None
        for port in [0, 1, 2]:
            print(f"[*] Probing camera port {port}...")
            temp_cap = cv2.VideoCapture(port, cv2.CAP_DSHOW)
            if temp_cap.isOpened():
                ret, _ = temp_cap.read()
                if ret:
                    print(f"[+] Camera locked on port {port}")
                    self.cap = temp_cap
                    break
            temp_cap.release()

        if self.cap is None:
            print("!!! FATAL: Could not establish camera feed. Check USB.")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.reset_state()
        self.buttons = {} 

        cv2.namedWindow("Production HUD", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Production HUD", self.handle_click)

    def reset_state(self):
        self.current_note = None   
        self.stable_count = 0      
        self.verification_status = "IDLE" 
        
        # 3-Step Security Protocol
        self.checklist = {
            "VISUAL": False,    
            "UV": False,        
            "WATERMARK": False  
        }

    def handle_click(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for name, (bx, by, bw, bh) in self.buttons.items():
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    if name == "RESET": 
                        print(">>> SYSTEM RESET")
                        self.reset_state()

    def draw_glass_panel(self, img, x, y, w, h, color=(0,0,0), alpha=0.6):
        sub = img[y:y+h, x:x+w]
        rect = np.full(sub.shape, color, dtype=np.uint8)
        res = cv2.addWeighted(sub, 1-alpha, rect, alpha, 1.0)
        cv2.rectangle(img, (x, y), (x+w, y+h), C_ACCENT, 1)
        img[y:y+h, x:x+w] = res

    def draw_button(self, img, text, x, y, w, h, bg_color=C_RED):
        sub = img[y:y+h, x:x+w]
        rect = np.full(sub.shape, bg_color, dtype=np.uint8)
        res = cv2.addWeighted(sub, 0.8, rect, 0.2, 1.0)
        img[y:y+h, x:x+w] = res
        cv2.rectangle(img, (x, y), (x+w, y+h), C_WHITE, 2)
        
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)
        tx = x + (w - tw) // 2
        ty = y + (h + th) // 2
        cv2.putText(img, text, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, 0.7, C_WHITE, 1)
        return (x, y, w, h)

    def run(self):
        print(">>> SYSTEM ACTIVE. AWAITING TARGET.")
        while True:
            ret, frame = self.cap.read()
            if not ret: break
            h, w = frame.shape[:2]
            
            # --- THE SQUARE CROP --- (Must match your training data exactly)
            crop_sz = min(h, w)
            cx, cy = w//2, h//2
            x1, y1 = cx - crop_sz//2, cy - crop_sz//2
            ai_crop = frame[y1:y1+crop_sz, x1:x1+crop_sz]
            
            top_label = "Scanning..."
            top_conf = 0.0
            valid_local = False
            
            try:
                # Run the Transformer at 640x640
                results = self.local_model.predict(ai_crop, imgsz=640, verbose=False)
                boxes = results[0].boxes
                
                # Extract the highest confidence detection
                if len(boxes) > 0:
                    best_box = boxes[0] 
                    top_conf = best_box.conf.item()
                    top_label = self.local_model.names[int(best_box.cls.item())]

                    if top_conf > CONF_THRESH:
                        valid_local = True
            except Exception as e: 
                # Fucking print the error instead of ignoring it
                print(f"[!] INFERENCE ERROR: {e}")

            # --- CORE LOGIC ---
            
            # Phase 1: Lock onto a valid note
            if self.verification_status == "IDLE":
                if valid_local and "real" in top_label:
                    detected_denom = top_label.split('_')[0]
                    if detected_denom == self.current_note:
                        self.stable_count += 1
                    else:
                        self.current_note = detected_denom
                        self.stable_count = 0
                else:
                    self.stable_count = 0
                    self.current_note = None

            # Trigger Checklist if locked
            if self.stable_count > STABILITY_FRAMES:
                self.verification_status = "CHECKLIST"
                self.checklist["VISUAL"] = True # Base identification secured

            # Phase 2: Verify security features
            if self.verification_status == "CHECKLIST":
                if valid_local:
                    if "uv_glowing" in top_label: 
                        self.checklist["UV"] = True
                    if "watermark" in top_label:
                        self.checklist["WATERMARK"] = True
                
                # Check if all protocols passed
                if all(self.checklist.values()):
                    self.verification_status = "GENUINE"

            # --- HUD RENDERING ---
            self.buttons = {} 
            
            color = C_ACCENT
            if self.verification_status == "CHECKLIST": color = C_ORANGE
            if self.verification_status == "GENUINE":   color = C_GREEN
            if self.verification_status == "REJECTED":  color = C_RED

            # Target Brackets
            l = 40
            cv2.line(frame, (x1, y1), (x1+l, y1), color, 4)
            cv2.line(frame, (x1, y1), (x1, y1+l), color, 4)
            cv2.line(frame, (x1+crop_sz, y1+crop_sz), (x1+crop_sz-l, y1+crop_sz), color, 4)
            cv2.line(frame, (x1+crop_sz, y1+crop_sz), (x1+crop_sz, y1+crop_sz-l), color, 4)

            # Top Status Bar
            bar_w, bar_h = 600, 80
            bar_x = (w - bar_w) // 2
            
            status_text = "ALIGN NOTE"
            if self.verification_status == "IDLE":
                if self.stable_count > 0: status_text = f"LOCKING: {self.stable_count}/{STABILITY_FRAMES}"
            elif self.verification_status == "CHECKLIST":
                status_text = f"VERIFYING: {self.current_note} INR"
            elif self.verification_status == "GENUINE":
                status_text = f"GENUINE {self.current_note} INR"
            elif self.verification_status == "REJECTED":
                status_text = "REJECTED"

            self.draw_glass_panel(frame, bar_x, 20, bar_w, bar_h, color=C_BLACK if color==C_ACCENT else color, alpha=0.8)
            (tw, th), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_DUPLEX, 1.0, 2)
            cv2.putText(frame, status_text, (bar_x + (bar_w - tw) // 2, 20 + (bar_h + th) // 2), cv2.FONT_HERSHEY_DUPLEX, 1.0, C_WHITE, 2)

            # Security Protocol Panel
            if self.verification_status in ["CHECKLIST", "GENUINE"]:
                list_w, list_h = 300, 300
                list_x = w - list_w - 30
                list_y = (h - list_h) // 2
                
                self.draw_glass_panel(frame, list_x, list_y, list_w, list_h, color=C_BLACK, alpha=0.7)
                cv2.putText(frame, "SECURITY PROTOCOLS", (list_x+20, list_y+40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, C_ACCENT, 2)
                
                sy = list_y + 90
                steps = [
                    ("VISUAL ID", self.checklist["VISUAL"]),
                    ("UV STRIP", self.checklist["UV"]),
                    ("WATERMARK", self.checklist["WATERMARK"])
                ]
                
                for label, is_done in steps:
                    icon = "[ OK ]" if is_done else "[....]"
                    col = C_GREEN if is_done else C_GRAY
                    
                    if not is_done and self.verification_status == "CHECKLIST":
                        if (int(time.time()*5) % 2 == 0): col = C_ORANGE

                    cv2.putText(frame, icon, (list_x+20, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
                    cv2.putText(frame, label, (list_x+110, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, C_WHITE, 1)
                    sy += 60

            # System Reset Button 
            if self.verification_status in ["GENUINE", "REJECTED"]:
                btn_w, btn_h = 200, 50
                btn_x = (w - btn_w) // 2
                btn_y = h - 80
                self.buttons["RESET"] = self.draw_button(frame, "RESET SYSTEM", btn_x, btn_y, btn_w, btn_h, C_RED)

            # Raw Detection Output
            if valid_local:
                cv2.putText(frame, f"RT-DETR: {top_label} ({int(top_conf*100)}%)", (30, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, C_WHITE, 1)

            cv2.imshow("Production HUD", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = EdgeVerifier()
    app.run()