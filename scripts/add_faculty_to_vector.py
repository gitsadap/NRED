"""
scripts/add_faculty_to_vector.py
================================
เพิ่มข้อมูลคณาจารย์จากฐานข้อมูลเข้าไปใน Vector Store
โดยใช้ program_code = "FACULTY" เพื่อแยกออกจากข้อมูลหลักสูตร

วิธีรัน:
    cd <project_root>
    python scripts/add_faculty_to_vector.py

ผลลัพธ์:
    - อัปเดต hf_cache/vector_meta.json และ hf_cache/vector_db.npy
    - chunk เดิม (BS-GEO, MS-NRE ฯลฯ) ยังคงอยู่ครบ
    - เพิ่ม chunk ใหม่สำหรับแต่ละคณาจารย์ด้วย program_code="FACULTY"
"""

import os, sys, json
import numpy as np

# เพิ่ม root ของโปรเจคเข้า sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from sentence_transformers import SentenceTransformer

HF_CACHE = os.path.join(BASE_DIR, "hf_cache")
META_PATH = os.path.join(HF_CACHE, "vector_meta.json")
NPY_PATH  = os.path.join(HF_CACHE, "vector_db.npy")


# ---------------------------------------------------------------------------
# โหลด embedding model
# ---------------------------------------------------------------------------
print("⏳ โหลด Embedding Model...")
model = SentenceTransformer(
    'paraphrase-multilingual-MiniLM-L12-v2',
    cache_folder=HF_CACHE,
    local_files_only=True,
)
print("✅ โหลด Model สำเร็จ")


# ---------------------------------------------------------------------------
# โหลด Vector Store เดิม
# ---------------------------------------------------------------------------
print("\n📂 โหลด Vector Store เดิม...")
with open(META_PATH, "r", encoding="utf-8") as f:
    existing_meta = json.load(f)
existing_embeddings = np.load(NPY_PATH, allow_pickle=False)

# ลบ FACULTY chunk เก่าออกก่อน (ถ้ามีจากการรันครั้งก่อน)
keep_idx = [i for i, m in enumerate(existing_meta) if m.get("program_code") != "FACULTY"]
existing_meta = [existing_meta[i] for i in keep_idx]
existing_embeddings = existing_embeddings[keep_idx]
print(f"  → chunk เดิม (หลักสูตร): {len(existing_meta)}")


# ---------------------------------------------------------------------------
# ดึงข้อมูลคณาจารย์จาก Database
# ---------------------------------------------------------------------------
print("\n🔌 เชื่อมต่อฐานข้อมูล...")
try:
    from app.database import SessionLocal
    from app.models import Faculty, Staff

    db = SessionLocal()
    faculty_rows = db.query(Faculty).all()
    staff_rows   = db.query(Staff).filter(Staff.type == "faculty").all()
    db.close()

    faculty_docs = []

    # ── Faculty (api.faculty) ──────────────────────────────────────────────
    for f in faculty_rows:
        full_name = f"{f.prefix or ''}{f.fname} {f.lname}".strip()
        en_name   = f"{f.fname_en or ''} {f.lname_en or ''}".strip()
        expertise = ""
        if isinstance(f.expertise, list):
            expertise = ", ".join(str(e) for e in f.expertise)
        elif isinstance(f.expertise, dict):
            expertise = str(f.expertise)

        text = (
            f"คณาจารย์: {full_name}"
            + (f" ({en_name})" if en_name else "")
            + (f"\nตำแหน่ง: {f.position}" if f.position else "")
            + (f"\nสังกัด/สาขา: {f.major}" if f.major else "")
            + (f"\nความเชี่ยวชาญ: {expertise}" if expertise else "")
            + (f"\nอีเมล: {f.email}" if f.email else "")
            + (f"\nตำแหน่งบริหาร: {f.admin_position}" if f.admin_position else "")
        )
        faculty_docs.append({
            "program_code": "FACULTY",
            "source": f"คณาจารย์: {full_name}",
            "parent_content": text,
            "small_fragment": text[:400],
        })

    # ── Staff (staff table) ────────────────────────────────────────────────
    for s in staff_rows:
        text = (
            f"บุคลากร/อาจารย์: {s.name}"
            + (f"\nตำแหน่ง: {s.position}" if s.position else "")
            + (f"\nความเชี่ยวชาญ: {s.expertise}" if s.expertise else "")
            + (f"\nอีเมล: {s.email}" if s.email else "")
        )
        faculty_docs.append({
            "program_code": "FACULTY",
            "source": f"บุคลากร: {s.name}",
            "parent_content": text,
            "small_fragment": text[:400],
        })

    print(f"  → ดึงข้อมูลได้: Faculty={len(faculty_rows)}, Staff={len(staff_rows)}")

except Exception as e:
    print(f"  ⚠️  เชื่อมต่อ DB ไม่สำเร็จ: {e}")
    print("  → ใช้ข้อมูล fallback จาก faculty_en.json แทน")

    # Fallback: ใช้ข้อมูลจาก JSON ถ้า DB ไม่พร้อม
    json_path = os.path.join(BASE_DIR, "faculty_en.json")
    faculty_docs = []
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            fac_data = json.load(f)
        for row in fac_data:
            name_th = row.get("original_name", "")
            name_en = row.get("name_en", "")
            text = f"คณาจารย์: {name_th}" + (f" ({name_en})" if name_en else "")
            faculty_docs.append({
                "program_code": "FACULTY",
                "source": f"คณาจารย์: {name_th}",
                "parent_content": text,
                "small_fragment": text,
            })
        print(f"  → อ่านจาก faculty_en.json: {len(faculty_docs)} คน")

if not faculty_docs:
    print("❌ ไม่มีข้อมูลคณาจารย์เลย หยุดการทำงาน")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Embed ข้อมูลคณาจารย์
# ---------------------------------------------------------------------------
texts = [d["small_fragment"] for d in faculty_docs]
print(f"\n🧠 กำลัง Embed ข้อมูลคณาจารย์ {len(texts)} รายการ...")
new_embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True).astype(np.float32)
print(f"  → Embedding shape: {new_embeddings.shape}")


# ---------------------------------------------------------------------------
# รวมกับ Vector Store เดิมและบันทึก
# ---------------------------------------------------------------------------
print("\n💾 รวมและบันทึก Vector Store...")
combined_meta = existing_meta + faculty_docs
combined_emb  = np.vstack([existing_embeddings, new_embeddings])

with open(META_PATH, "w", encoding="utf-8") as f:
    json.dump(combined_meta, f, ensure_ascii=False)
np.save(NPY_PATH, combined_emb, allow_pickle=False)

print(f"\n✅ เสร็จสมบูรณ์!")
print(f"   chunk หลักสูตร : {len(existing_meta)}")
print(f"   chunk FACULTY  : {len(faculty_docs)}")
print(f"   รวมทั้งหมด     : {len(combined_meta)}")
print(f"   Embedding shape: {combined_emb.shape}")
