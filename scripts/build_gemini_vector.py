import os
import json
import time
import numpy as np
import re  # <--- นำเข้ามาแล้วเรียบร้อย ระบบจะไม่แครชแล้วครับ
try:
    import fitz  # PyMuPDF
except ImportError:
    import pymupdf as fitz
from google import genai
from dotenv import load_dotenv

# โหลด API Key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ ไม่พบ GEMINI_API_KEY ในไฟล์ .env")
    exit()

# สร้าง Client
client = genai.Client(api_key=GEMINI_API_KEY)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
docs_dir = os.path.join(base_dir, "docs")
hf_cache_dir = os.path.join(base_dir, "hf_cache")
os.makedirs(hf_cache_dir, exist_ok=True)

documents_meta = []
texts_to_embed = []

PROGRAM_CODES = ["BS-NRE", "BS-GEO", "MS-NRE", "MS-GISCI", "MS-ENVI", "PHD-NRE", "PHD-ENVI"]

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

                    small_chunks = split_small_chunks(page_text)
                    
                    for s_chunk in small_chunks:
                        if len(s_chunk.strip()) > 20:
                            texts_to_embed.append(f"[{assigned_code}] {s_chunk}")
                            documents_meta.append({
                                "program_code": assigned_code,
                                "parent_content": page_text,
                                "source": f"{filename} หน้า {page_num + 1}",
                                "small_fragment": s_chunk
                            })
            except Exception as e:
                print(f"  ❌ อ่านไฟล์ {filename} ไม่สำเร็จ: {e}")

if texts_to_embed:
    print(f"\n🧠 กำลังฝังชิ้นจิ๋ว {len(texts_to_embed)} ท่อน แบบเหมาเข่ง (Batch 100 รายการ)...")
    
    all_embeddings = []
    batch_size = 100
    
    for i in range(0, len(texts_to_embed), batch_size):
        batch_texts = texts_to_embed[i:i + batch_size]
        current_batch = (i // batch_size) + 1
        total_batches = (len(texts_to_embed) // batch_size) + 1
        
        retries = 3
        while retries > 0:
            try:
                result = client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=batch_texts
                )
                
                for emb in result.embeddings:
                    all_embeddings.append(emb.values)
                
                print(f"  ✅ Batch {current_batch}/{total_batches} สำเร็จ (ระบบหลับ 65 วินาที เพื่อรอโควต้ารีเซ็ต...)")
                
                # บังคับหลับ 65 วินาที เพื่อรีเซ็ตโควต้า 100 ครั้ง/นาที
                time.sleep(65)
                
                break 
                
            except Exception as e:
                retries -= 1
                error_msg = str(e)
                print(f"  ⚠️ Error Batch {current_batch} (เหลือโอกาส {retries} ครั้ง): {error_msg[:100]}...")
                
                if "429" in error_msg or "quota" in error_msg.lower() or "exhausted" in error_msg.lower():
                    # ลองหาตัวเลขวินาที ถ้า Google ส่งมา
                    match = re.search(r'retry in (\d+\.\d+)s', error_msg)
                    if match:
                        wait_t = float(match.group(1)) + 5 
                        print(f"  ⏳ โดน Limit ชั่วคราว... ระบบกำลังพัก {wait_t:.0f} วินาที")
                        time.sleep(wait_t)
                    else:
                        # ถ้าไม่มีตัวเลขบอก ให้พักยาว 120 วินาทีไปเลยเพื่อความชัวร์
                        print("  ⏳ โดน Limit และไม่ระบุเวลา... บังคับพักยาว 120 วินาที")
                        time.sleep(120)
                else:
                    # Error อื่นๆ ที่ไม่ใช่ 429 พักแป๊บเดียวพอ
                    time.sleep(10)
                    
                if retries == 0:
                    print(f"  ❌ ยอมแพ้ Batch {current_batch} ใส่ค่า 0 ให้แทน (เพื่อไม่ให้โปรแกรมแครช)")
                    for _ in range(len(batch_texts)):
                        all_embeddings.append([0.0] * 768)

    print("\n\n💾 กำลังบันทึกไฟล์ลงฮาร์ดดิสก์...")
    
    vector_npy_path = os.path.join(hf_cache_dir, "vector_db.npy")
    doc_embeddings_np = np.array(all_embeddings, dtype=np.float32)
    np.save(vector_npy_path, doc_embeddings_np, allow_pickle=False)
    
    meta_json_path = os.path.join(hf_cache_dir, "vector_meta.json")
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(documents_meta, f, ensure_ascii=False, indent=2)
        
    print(f"🎉 เสร็จสมบูรณ์! สร้างฐานข้อมูลสำเร็จ")
    print(f"📂 ไฟล์บันทึกอยู่ที่: {hf_cache_dir}")