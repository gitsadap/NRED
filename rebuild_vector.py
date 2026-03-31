import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 1. ตั้งค่า Path
base_dir = os.path.dirname(os.path.abspath(__file__))
hf_cache_dir = os.path.join(base_dir, "hf_cache")
# สมมติว่าคุณมีไฟล์ต้นฉบับข้อมูลดิบ (Raw Data) อยู่ หรือใช้จาก meta เดิม
meta_path = os.path.join(hf_cache_dir, "vector_meta.pkl") 
vector_out_path = os.path.join(hf_cache_dir, "vector_db.pkl")
new_meta_out_path = os.path.join(hf_cache_dir, "vector_meta_new.pkl")

print("--- เริ่มกระบวนการสร้าง Smart Vector (Numpy + LangChain) ---")

try:
    if not os.path.exists(meta_path):
        print(f"❌ ไม่พบไฟล์ {meta_path}")
        exit()

    with open(meta_path, "rb") as f:
        old_documents_meta = pickle.load(f)
    
    # 2. ตั้งค่าการแบ่งข้อความ (หัวใจของความฉลาด)
    # chunk_size: ขนาดแต่ละส่วน (600-800 กำลังดีสำหรับตาราง)
    # chunk_overlap: ให้เนื้อหาเกยกันเล็กน้อยเพื่อไม่ให้บริบทขาดหาย
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )

    smart_meta = []
    texts_to_embed = []

    print(f"📦 กำลังประมวลผลข้อมูลจาก {len(old_documents_meta)} หน้าเดิม...")

    for meta in old_documents_meta:
        content = meta.get('parent_content', '') or meta.get('content', '')
        if not content: continue

        # หั่นข้อความให้ละเอียดขึ้น
        chunks = text_splitter.split_text(content)
        
        for chunk in chunks:
            texts_to_embed.append(chunk)
            # เก็บ Metadata เดิมไว้แต่เปลี่ยนเนื้อหาเป็น Chunk ที่หั่นแล้ว
            new_entry = meta.copy()
            new_entry['parent_content'] = chunk
            smart_meta.append(new_entry)

    print(f"⚡ หั่นข้อมูลเสร็จสิ้น: ได้ทั้งหมด {len(texts_to_embed)} Chunks (ละเอียดขึ้นมาก)")

    # 3. สร้าง Embedding
    print("🤖 กำลังโหลด Model และสร้าง Vectors...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder=hf_cache_dir)
    embeddings = model.encode(texts_to_embed, convert_to_numpy=True, show_progress_bar=True)

    # 4. บันทึกไฟล์ใหม่
    with open(vector_out_path, "wb") as f:
        pickle.dump(embeddings, f)
    with open(meta_path, "wb") as f: # เขียนทับ meta เดิมไปเลย
        pickle.dump(smart_meta, f)

    print(f"✅ สำเร็จ! Vector DB ใหม่ฉลาดขึ้นและละเอียดขึ้นแล้ว")
    print(f"📏 จำนวน Vectors: {len(embeddings)}")

except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {e}")