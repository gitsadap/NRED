import os
import pickle
import numpy as np  # 🌟 ใช้ numpy แทน torch เพื่อประหยัดพื้นที่บน Vercel
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from app.logging_config import logger 
from typing import List, Dict, Optional
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["Chatbot AI"])

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    level: Optional[str] = None     
    program: Optional[str] = None   

def get_program_code(level: str, program: str) -> str:
    mapping = {
        ("ปริญญาตรี", "ทรัพยากรธรรมชาติและสิ่งแวดล้อม (NRE)"): "BS-NRE",
        ("ปริญญาตรี", "ภูมิศาสตร์ (GEO)"): "BS-GEO",
        ("ปริญญาโท", "ทรัพยากรธรรมชาติและสิ่งแวดล้อม (NRE)"): "MS-NRE",
        ("ปริญญาโท", "ภูมิสารสนเทศ (GISCI)"): "MS-GISCI",
        ("ปริญญาโท", "วิทยาศาสตร์สิ่งแวดล้อม (ENVI)"): "MS-ENVI",
        ("ปริญญาเอก", "ทรัพยากรธรรมชาติและสิ่งแวดล้อม (NRE)"): "PHD-NRE",
        ("ปริญญาเอก", "วิทยาศาสตร์สิ่งแวดล้อม (ENVI)"): "PHD-ENVI"
    }
    return mapping.get((level, program))

# Load Models
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
hf_cache_dir = os.path.join(base_dir, "hf_cache")
os.environ["HF_HOME"] = hf_cache_dir

ai_model = None
doc_embeddings = None
documents_meta = []

try:
    meta_path = os.path.join(hf_cache_dir, "vector_meta.pkl")
    vector_path = os.path.join(hf_cache_dir, "vector_db.pkl")
    
    if os.path.exists(meta_path) and os.path.exists(vector_path):
        with open(meta_path, "rb") as f:
            documents_meta = pickle.load(f)
        with open(vector_path, "rb") as f:
            doc_embeddings = pickle.load(f)
            # มั่นใจว่าเป็น numpy array สำหรับการคำนวณ
            doc_embeddings = np.array(doc_embeddings)
        
        # โหลดโมเดล SentenceTransformer (รันบน CPU)
        ai_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder=hf_cache_dir, device='cpu')
        logger.info("✅ Chatbot Vector Database & Model loaded")
except Exception as e:
    logger.error(f"❌ Failed to load AI models: {e}")

def expand_query(query: str) -> str:
    replacements = {
        "EIA": "EIA การประเมินผลกระทบสิ่งแวดล้อม Environmental Impact Assessment",
        "GIS": "Geographic Information System",
        "IoT": "Internet of Things",
        "วิชาดิน": "ปฐพีวิทยา",
        "วิจัย": "ระเบียบวิธีวิจัย",
        "ปี 1": "ชั้นปีที่ 1", "ปี 2": "ชั้นปีที่ 2", "ปี 3": "ชั้นปีที่ 3", "ปี 4": "ชั้นปีที่ 4",
        "เทอม 1": "ภาคเรียนที่ 1", "เทอม 2": "ภาคเรียนที่ 2", "ซัมเมอร์": "ภาคเรียนที่ 3"
    }
    for short, full in replacements.items():
        if short.upper() in query.upper():
            query = query + " " + full
    return query

@router.post("/chatbot")
async def get_chatbot_response(req: ChatRequest):
    user_msg = req.message.strip()
    if not user_msg: return {"response": "กรุณาพิมพ์คำถามครับ"}
    
    # Check if models are ready
    if ai_model is None or doc_embeddings is None:
        return {"response": "ขออภัยค่ะ ระบบฐานความรู้ยังไม่พร้อมใช้งาน (Model/Vector missing)"}

    try:
        search_query = expand_query(user_msg)
        target_code = get_program_code(req.level, req.program)
        
        # กรองข้อมูลเฉพาะหลักสูตรที่เลือก
        indices = [i for i, m in enumerate(documents_meta) if m.get("program_code") == target_code]
        if not indices:
            return {"response": f"ขออภัยค่ะ ยังไม่มีข้อมูลของหลักสูตร {target_code}"}

        filtered_embeddings = doc_embeddings[indices]
        filtered_meta = [documents_meta[i] for i in indices]

        # 🔍 สร้าง Embedding จากคำถาม (Numpy)
        query_embedding = ai_model.encode(search_query)

        # 🌟 คำนวณ Cosine Similarity ด้วย Numpy
        norm_query = np.linalg.norm(query_embedding)
        norm_filtered = np.linalg.norm(filtered_embeddings, axis=1)
        # ป้องกันการหารด้วยศูนย์
        denom = norm_filtered * norm_query
        denom[denom == 0] = 1e-9
        scores = np.dot(filtered_embeddings, query_embedding) / denom
        
        # เลือก Top 15 ที่ใกล้เคียงที่สุด
        top_indices = np.argsort(scores)[::-1][:15]
        
        seen_pages = set()
        final_contexts = []
        
        for idx in top_indices:
            if scores[idx] > 0.12: # Threshold ตามเดิมของคุณ
                meta = filtered_meta[idx]
                if meta['source'] not in seen_pages:
                    final_contexts.append(f"อ้างอิงจาก {meta['source']}:\n{meta['parent_content']}")
                    seen_pages.add(meta['source'])
            if len(final_contexts) >= 6: break

        if not final_contexts:
            return {"response": f"ไม่พบข้อมูลที่เกี่ยวข้องกับ '{user_msg}' ในฐานข้อมูล {target_code}"}

        full_context_text = "\n\n---\n\n".join(final_contexts)
        
        # --- เรียกใช้ Gemini ตัวเดิมที่คุณต้องการ ---
        gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            # กลับมาใช้รุ่นเดิมตามที่คุณต้องการ
            model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
            
            prompt = f"""
คุณคือผู้ช่วยอัจฉริยะสาวประจำภาควิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม มหาวิทยาลัยนเรศวร
หน้าที่: ตอบคำถามนิสิตเกี่ยวกับหลักสูตร {target_code}
กฎการตอบ: 
1. ใช้ข้อมูลจาก 'ข้อมูลอ้างอิง' เท่านั้น
2. พยายามสรุปรายวิชาหรือเนื้อหาออกมาเป็นรายการให้สวยงาม
3. ตอบสั้นๆ เข้าใจง่าย และมีความเป็นกันเองแต่สุภาพ

ข้อมูลอ้างอิง:
{full_context_text}

คำถามจากนิสิต: {user_msg}
"""
            response = model.generate_content(prompt)
            return {"response": response.text}
            
        return {"response": "พี่ AI ขัดข้องเรื่อง API Key ค่ะ ฝากแจ้งแอดมินทีนะคะ"}
            
    except Exception as e:
        logger.error(f"Chatbot Error: {e}")
        return {"response": f"เกิดข้อผิดพลาด: {str(e)}"}