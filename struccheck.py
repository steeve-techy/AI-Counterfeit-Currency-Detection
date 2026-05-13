import os

# --- CONFIG ---
# Point this to where your capture script just saved the images
DATA_DIR = "raw_downloads" 

def audit_dataset():
    if not os.path.exists(DATA_DIR):
        print(f"!!! FATAL: Folder '{DATA_DIR}' does not exist.")
        return

    print(f"\n>>> AUDITING DATASET STRUCTURE: {DATA_DIR}\n")
    
    total_images = 0
    class_counts = {}

    # Grab all the class folders
    classes = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
    
    if not classes:
        print("[-] Error: No class folders found inside.")
        return

    print(f"{'CLASS NAME'.ljust(20)} | {'IMAGE COUNT'}")
    print("-" * 40)

    for cls in sorted(classes):
        class_path = os.path.join(DATA_DIR, cls)
        
        # Count only valid image formats
        images = [f for f in os.listdir(class_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        count = len(images)
        
        class_counts[cls] = count
        total_images += count
        
        print(f"{cls.ljust(20)} | {count}")

    print("-" * 40)
    print(f"{'TOTAL IMAGES'.ljust(20)} | {total_images}\n")
    
    # --- HEALTH CHECKS ---
    if total_images == 0:
        print("!!! WARNING: Your dataset is completely empty.")
    else:
        empty_classes = [c for c, count in class_counts.items() if count == 0]
        if empty_classes:
            print(f"!!! WARNING: You have empty classes! Go shoot images for: {', '.join(empty_classes)}")
        else:
            print("[+] Structure is bulletproof. Ready for YOLO/RT-DETR formatting.")

if __name__ == "__main__":
    audit_dataset()