import os
import shutil
import random
from pathlib import Path

# --- CONFIGURATION ---
SOURCE_DIR = r"raw_downloads"
DEST_DIR = r"dataset_v2"
TRAIN_RATIO = 0.8  

# EXACT list of target classes (Notice 'empty' is NOT here. YOLO handles backgrounds implicitly)
TARGET_CLASSES = [
    "10_real", "20_real", "50_real", "100_real", 
    "200_real", "500_real", "uv_glowing", "watermark"
]

def setup_folders():
    if os.path.exists(DEST_DIR):
        shutil.rmtree(DEST_DIR)
        
    for split in ['train', 'val']:
        os.makedirs(f"{DEST_DIR}/{split}/images", exist_ok=True)
        os.makedirs(f"{DEST_DIR}/{split}/labels", exist_ok=True)

def process_folder(folder_name):
    src_folder = Path(SOURCE_DIR) / folder_name
    if not src_folder.exists():
        return

    images = [f for f in os.listdir(src_folder) if f.lower().endswith(('.jpg', '.png'))]
    random.shuffle(images)
    
    train_split = int(len(images) * TRAIN_RATIO)
    print(f"[+] Processing {folder_name}: Formatting {len(images)} images...")

    for i, img_name in enumerate(images):
        split = 'train' if i < train_split else 'val'
        
        # 1. Copy Image
        src_img = src_folder / img_name
        dest_img = Path(DEST_DIR) / split / "images" / f"{folder_name}_{img_name}"
        shutil.copy2(src_img, dest_img)
        
        # 2. Generate Label
        label_name = dest_img.stem + ".txt"
        label_path = Path(DEST_DIR) / split / "labels" / label_name
        
        with open(label_path, 'w') as f:
            if folder_name == "empty":
                # Backgrounds get blank text files
                pass 
            elif folder_name in TARGET_CLASSES:
                # Notes get a full-frame bounding box
                class_id = TARGET_CLASSES.index(folder_name)
                f.write(f"{class_id} 0.5 0.5 1.0 1.0\n")

def generate_yaml():
    yaml_path = Path(DEST_DIR) / "data.yaml"
    abs_path = Path(DEST_DIR).absolute().as_posix()
    
    yaml_content = f"""path: {abs_path}
train: train/images
val: val/images

nc: {len(TARGET_CLASSES)}
names:
"""
    for i, name in enumerate(TARGET_CLASSES):
        yaml_content += f"  {i}: {name}\n"
        
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    print(f"\n[+] Generated data.yaml successfully.")

if __name__ == "__main__":
    print(">>> BUILDING PRODUCTION RT-DETR DATASET...\n")
    setup_folders()
    
    # Process valid classes
    for cls in TARGET_CLASSES:
        process_folder(cls)
        
    # Process the empty background class
    process_folder("empty")
        
    generate_yaml()
    print("\n>>> DONE. 'dataset_v2' is locked, loaded, and ready for training.")