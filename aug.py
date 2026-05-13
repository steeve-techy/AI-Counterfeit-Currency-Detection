import cv2
import os
import random
import numpy as np
import uuid
import shutil

# --- CONFIGURATION ---
SOURCE_DIR = "raw_downloads"
DEST_DIR = "dataset_final_sharp" # Injecting into the existing dataset

# How many copies to make per image?
MULTIPLIER_NORMAL = 5    # For 10_real, 50_real, etc.
MULTIPLIER_HEAVY = 10    # For uv_glowing, watermark (Since we have 0 old data)

# Image settings (Must match your training)
IMG_SIZE = 224

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def augment_image(image, intensity="normal"):
    """
    Applies augmentation. 
    intensity="normal": Light rotation, brightness (For notes)
    intensity="heavy":  Harder rotation, noise, blur (For UV/Watermark)
    """
    h, w = image.shape[:2]
    
    # 1. Rotation
    angle_limit = 5 if intensity == "normal" else 20
    angle = random.uniform(-angle_limit, angle_limit)
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    img_aug = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    
    # 2. Brightness/Contrast
    # UV/Watermark needs huge variance because lighting is tricky
    alpha_limit = 0.2 if intensity == "normal" else 0.4 
    alpha = 1.0 + random.uniform(-alpha_limit, alpha_limit) # Contrast
    beta = random.randint(-20, 20) if intensity == "normal" else random.randint(-40, 40) # Brightness
    img_aug = cv2.convertScaleAbs(img_aug, alpha=alpha, beta=beta)
    
    # 3. Noise (Heavy only)
    if intensity == "heavy" and random.random() > 0.5:
        noise = np.random.normal(0, 15, img_aug.shape).astype(np.uint8)
        img_aug = cv2.add(img_aug, noise)

    # 4. Blur (Heavy only - simulates out of focus macro)
    if intensity == "heavy" and random.random() > 0.7:
        k = random.choice([3, 5])
        img_aug = cv2.GaussianBlur(img_aug, (k, k), 0)

    return img_aug

def process_injection():
    print(f">>> STARTING DATA INJECTION")
    print(f"    Source: {SOURCE_DIR}")
    print(f"    Target: {DEST_DIR}")

    # specific classes found in your screenshot
    target_folders = [f for f in os.listdir(SOURCE_DIR) if os.path.isdir(os.path.join(SOURCE_DIR, f))]
    
    for class_name in target_folders:
        src_path = os.path.join(SOURCE_DIR, class_name)
        images = [f for f in os.listdir(src_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        
        if not images:
            continue

        # Determine strategy
        if class_name in ["uv_glowing", "watermark"]:
            multiplier = MULTIPLIER_HEAVY
            mode = "heavy"
            print(f"\n>>> PROCESSING {class_name} (HEAVY MODE x{multiplier})")
        else:
            multiplier = MULTIPLIER_NORMAL
            mode = "normal"
            print(f"\n>>> PROCESSING {class_name} (NORMAL MODE x{multiplier})")

        count_new = 0
        
        for img_name in images:
            img_path = os.path.join(src_path, img_name)
            original_img = cv2.imread(img_path)
            
            if original_img is None: continue
            
            # Resize once
            original_img = cv2.resize(original_img, (IMG_SIZE, IMG_SIZE))

            # Generate Copies
            for i in range(multiplier):
                aug_img = augment_image(original_img, intensity=mode)
                
                # Split Train (80%) / Val (20%)
                split = "train" if random.random() < 0.8 else "val"
                
                # Destination Path
                # e.g. dataset_final_sharp/train/uv_glowing/
                dest_folder = os.path.join(DEST_DIR, split, class_name)
                ensure_dir(dest_folder)
                
                # Unique Name to prevent overwriting old data
                new_filename = f"new_{class_name}_{uuid.uuid4().hex[:8]}.jpg"
                cv2.imwrite(os.path.join(dest_folder, new_filename), aug_img)
                
                count_new += 1
                
        print(f"    + Injected {count_new} images into {class_name}")

    print("\n>>> INJECTION COMPLETE.")
    print("    You can now run 'train_cpu_final.py' to fine-tune.")

if __name__ == "__main__":
    process_injection()