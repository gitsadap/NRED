import os
import pickle
import torch
try:
    import fitz  # พยายามเรียกแบบมาตรฐาน
except ImportError:
    import pymupdf as fitz  # ถ้าไม่ได้ ให้เรียกผ่านชื่อแพ็กเกจโดยตรง
from sentence_transformers import SentenceTransformer

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
docs_dir = os.path.join(base_dir, "docs")
hf_cache_dir = os.path.join(base_dir, "hf_cache")
os.makedirs(hf_cache_dir, exist_ok=True)

print("⏳ กำลังโหลด AI Embedding Model...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder=hf_cache_dir, device='cpu')

documents_meta = []
texts_to_embed = []

PROGRAM_CODES = ["BS-NRE", "BS-GEO", "MS-NRE", "MS-GISCI", "MS-ENVI", "PHD-NRE", "PHD-ENVI"]

# 🌟 ฟังก์ชันหั่นชิ้นจิ๋ว (Small Chunks) สำหรับค้นหา
def split_small_chunks(text, size=400, overlap=150):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

print("\n📄 เริ่มต้นวิเคราะห์ PDF แบบ Small-to-Big...")

for root, dirs, files in os.walk(docs_dir):
    for filename in files:
        if filename.endswith(".pdf"):
            file_path = os.path.join(root, filename)
            assigned_code = next((c for c in PROGRAM_CODES if c.upper() in filename.upper()), None)
            
            if not assigned_code: continue
                
            print(f"  -> อ่านไฟล์: {filename} [รหัส: {assigned_code}]")
            try:
                doc = fitz.open(file_path)
                for page_num in range(len(doc)):
                    page_text = doc[page_num].get_text("text").strip()
                    if len(page_text) < 50: continue

                    # 🌟 1. เก็บ "หน้าเต็ม" (Big Chunk) ไว้ใน Metadata
                    page_id = f"{filename}_p{page_num}"
                    
                    # 🌟 2. หั่นหน้าเต็มนันเป็น "ชิ้นจิ๋ว" (Small Chunks)
                    small_chunks = split_small_chunks(page_text)
                    
                    for s_chunk in small_chunks:
                        if len(s_chunk.strip()) > 20:
                            # เราจะ Embed เฉพาะชิ้นจิ๋ว
                            texts_to_embed.append(f"[{assigned_code}] {s_chunk}")
                            documents_meta.append({
                                "program_code": assigned_code,
                                "parent_content": page_text, # 🌟 เก็บเนื้อหาทั้งหน้าไว้ที่นี่
                                "source": f"{filename} หน้า {page_num + 1}",
                                "small_fragment": s_chunk
                            })
            except Exception as e:
                print(f"  ❌ อ่านไฟล์ {filename} ไม่สำเร็จ: {e}")

if texts_to_embed:
    print(f"\n🧠 กำลังฝังชิ้นจิ๋ว {len(texts_to_embed)} ท่อน ลงใน Vector DB...")
    doc_embeddings = model.encode(texts_to_embed, convert_to_tensor=True)
    torch.save(doc_embeddings, os.path.join(hf_cache_dir, "vector_db.pt"))
    with open(os.path.join(hf_cache_dir, "vector_meta.pkl"), "wb") as f:
        pickle.dump(documents_meta, f)
    print(f"✅ เสร็จสมบูรณ์! สร้างฐานข้อมูลแบบ Small-to-Big สำเร็จ")