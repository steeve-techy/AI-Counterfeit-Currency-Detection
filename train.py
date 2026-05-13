from ultralytics import RTDETR

def train_transformer():
    print(">>> INITIALIZING FINAL RT-DETR VISION TRANSFORMER...")
    
    # Using the V1 Large model
    model = RTDETR('rtdetr-l.pt') 

    results = model.train(
        # --- MAKE SURE THIS ABSOLUTE PATH IS CORRECT ---
        data=r'Z:\Lenovo\Coding\fakecurrencyyolo\new mode\dataset_v2\data.yaml', 
        
        project='currency_transformer_runs',
        name='rtdetr_v2_cam_fix', # New run name so we don't overwrite the old one
        
        epochs=50,      
        patience=10,    
        
        imgsz=640,      
        
        # --- ANTI-CRASH MEASURES ---
        batch=4,        
        workers=1,      
        cache=False,    
        
        device=0,       
        optimizer='AdamW', 
        lr0=0.0001
    )

    print(">>> TRANSFORMER TRAINING COMPLETE.")

if __name__ == '__main__':
    train_transformer()