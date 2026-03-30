import os
import pickle
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai
from app.logging_config import logger # 🌟 เพิ่มการ Import logger
from typing import List, Dict, Optional
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["Chatbot AI"])

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    level: Optional[str] = None     
    program: Optional[str] = None   

# 🌟 ฟังก์ชันแปลงชื่อปุ่มเป็นรหัส (ที่หายไปใน Error)
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
os.environ["HF_HUB_OFFLINE"] = "1"

ai_model = None
doc_embeddings = None
documents_meta = []

try:
    tensor_path = os.path.join(hf_cache_dir, "vector_db.pt")
    meta_path = os.path.join(hf_cache_dir, "vector_meta.pkl")
    if os.path.exists(tensor_path) and os.path.exists(meta_path):
        doc_embeddings = torch.load(tensor_path, map_location=torch.device('cpu'), weights_only=True)
        with open(meta_path, "rb") as f:
            documents_meta = pickle.load(f)
        ai_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder=hf_cache_dir, device='cpu')
except Exception as e:
    if 'logger' in globals():
        logger.error(f"Failed to load AI models: {e}")


def expand_query(query: str) -> str:
    # ดักคำย่อที่เด็กชอบใช้ในภาควิชา
    replacements = {
        "EIA": "EIA การประเมินผลกระทบสิ่งแวดล้อม Environmental Impact Assessment",
        "GIS": "Geographic Information System",
        "IoT": "Internet of Things",
        "วิชาดิน": "ปฐพีวิทยา",
        "วิจัย": "ระเบียบวิธีวิจัย",
        "ปี 1": "ชั้นปีที่ 1",
        "ปี 2": "ชั้นปีที่ 2",
        "ปี 3": "ชั้นปีที่ 3",
        "ปี 4": "ชั้นปีที่ 4",
        "เทอม 1": "ภาคเรียนที่ 1",
        "เทอม 2": "ภาคเรียนที่ 2",
        "ซัมเมอร์": "ภาคเรียนที่ 3"
    }
    for short, full in replacements.items():
        if short.upper() in query.upper():
            query = query + " " + full
    return query

@router.post("/chatbot")
@router.post("/chatbot")
async def get_chatbot_response(req: ChatRequest):
    user_msg = req.message.strip()
    if not user_msg: return {"response": "กรุณาพิมพ์คำถามครับ"}
    
    try:
        # 🌟 เรียกใช้ expand_query เพื่อช่วยค้นหา EIA และ ปี 1
        search_query = expand_query(user_msg)
        
        target_code = get_program_code(req.level, req.program)
        valid_indices = [i for i, meta in enumerate(documents_meta) if meta.get("program_code") == target_code]
        
        if not valid_indices:
            return {"response": f"ขออภัยครับ ยังไม่มีข้อมูลของหลักสูตร {target_code}"}

        filtered_embeddings = doc_embeddings[valid_indices]
        filtered_meta = [documents_meta[i] for i in valid_indices]

        # 🔍 ใช้ search_query ในการสร้าง Vector (จะแม่นยำกว่าใช้ user_msg ตรงๆ)
        query_embedding = ai_model.encode(search_query, convert_to_tensor=True)
        cosine_scores = util.cos_sim(query_embedding, filtered_embeddings)[0]
        
        topk = torch.topk(cosine_scores, k=min(15, len(cosine_scores)))
        
        seen_pages = set()
        final_contexts = []
        
        for score, idx in zip(topk.values, topk.indices):
            # ใช้ 0.12 ตามที่อาจารย์ตั้งไว้ (ดีแล้วครับสำหรับตาราง)
            if score.item() > 0.12: 
                meta = filtered_meta[idx.item()]
                page_id = meta['source'] 
                
                if page_id not in seen_pages:
                    final_contexts.append(f"อ้างอิงจาก {meta['source']}:\n{meta['parent_content']}")
                    seen_pages.add(page_id)
            
            if len(final_contexts) >= 6: # ส่ง 6 หน้า ตามที่คุยกัน
                break

        if not final_contexts:
            return {"response": f"ขออภัยค่ะ ไม่พบข้อมูลที่เกี่ยวข้องกับ '{user_msg}' ในหลักสูตร {target_code}"}

        full_context_text = "\n\n---\n\n".join(final_contexts)
        
        gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            # ใช้รุ่นที่อยู่ในลิสต์ของอาจารย์ (flash-lite-preview)
            model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
            
            prompt = f"""
คุณคือผู้ช่วยอัจฉริยะสาวประจำภาควิชา มหาวิทยาลัยนเรศวร
หน้าที่: ตอบคำถามนิสิตเกี่ยวกับหลักสูตร {target_code}
กฎการตอบ: 
1. ใช้ข้อมูลจาก 'ข้อมูลอ้างอิง' เท่านั้น
2. ในข้อมูลอ้างอิงอาจจะแสดงผลเป็นตารางหรือข้อความที่อ่านยาก ให้พยายามถอดรหัสรายวิชาออกมา
3. ถ้าพบชื่อวิชาและรหัสวิชา ให้สรุปออกมาเป็นรายการ
4. ถ้าไม่มีข้อมูลในนั้น ให้ตอบว่าไม่พบข้อมูลและแนะนำให้ติดต่ออาจารย์ที่ปรึกษา
5. ตอบเป็นข้อๆ สั้นๆ ให้เข้าใจง่ายและสุภาพ

ข้อมูลอ้างอิง:
{full_context_text}

คำถามจากนิสิต: {user_msg}
"""
            response = model.generate_content(prompt)
            return {"response": response.text}
            
        return {"response": "ระบบ AI ขัดข้อง พี่ขอตัวไปพักก่อนนะคะ"}
            
    except Exception as e:
        logger.error(f"Chatbot Error: {e}")
        return {"response": f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)}"}