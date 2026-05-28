import torch
import pickle
import os

# ระบุ Path ของไฟล์เดิม
hf_cache_dir = "hf_cache"  # ปรับให้ตรงกับที่เก็บไฟล์ของคุณ
old_file = os.path.join(hf_cache_dir, "vector_db.pt")
new_file = os.path.join(hf_cache_dir, "vector_db.pkl")

if os.path.exists(old_file):
    print(f"กำลังโหลดไฟล์: {old_file}")
    # โหลดไฟล์ Tensor
    embeddings = torch.load(old_file, map_location='cpu', weights_only=True)
    
    # แปลงเป็น Numpy Array
    embeddings_numpy = embeddings.numpy()
    
    # เซฟเป็นไฟล์ .pkl (Pickle)
    with open(new_file, "wb") as f:
        pickle.dump(embeddings_numpy, f)
    
    print(f"✅ แปลงไฟล์สำเร็จ! ไฟล์ใหม่อยู่ที่: {new_file}")
    print(f"ขนาดไฟล์: {os.path.getsize(new_file) / (1024*1024):.2f} MB")
else:
    print("❌ ไม่พบไฟล์ vector_db.pt")