import pickle
import os

meta_path = 'hf_cache/vector_meta.pkl'

if os.path.exists(meta_path):
    with open(meta_path, 'rb') as f:
        data = pickle.load(f)
    
    print(f"Total chunks in DB: {len(data)}")
    print("-" * 50)
    
    # สุ่มดูข้อมูล 3 ชิ้นแรก
    for i in range(min(3, len(data))):
        print(f"Chunk {i+1} | Source: {data[i]['source']}")
        print(f"Content Preview:\n{data[i]['parent_content'][:1000]}") # ดู 1000 ตัวอักษรแรก
        print("-" * 50)
else:
    print("ไม่พบไฟล์ vector_meta.pkl กรุณารัน build_vector_db.py ก่อนครับ")