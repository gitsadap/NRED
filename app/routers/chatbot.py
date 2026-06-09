import os
import pickle
import json
import time  
import numpy as np  
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import litellm
from app.logging_config import logger 
from typing import List, Dict, Optional
from app.config import settings
from sentence_transformers import SentenceTransformer


try:
    embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder="hf_cache", local_files_only=True)
except Exception as e:
    logger.error(f"❌ Failed to load SentenceTransformer (No internet or cache missing): {e}")
    try:
        
        embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder="hf_cache")
    except Exception as e2:
        logger.error(f"❌ Fallback failed too: {e2}")
        embedding_model = None

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


base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
hf_cache_dir = os.path.join(base_dir, "hf_cache")


doc_embeddings = None
documents_meta = []

try:
    meta_json_path = os.path.join(hf_cache_dir, "vector_meta.json")
    vector_npy_path = os.path.join(hf_cache_dir, "vector_db.npy")

    meta_pkl_path = os.path.join(hf_cache_dir, "vector_meta.pkl")
    vector_pkl_path = os.path.join(hf_cache_dir, "vector_db.pkl")
    
    loaded = False

    
    if os.path.exists(meta_json_path) and os.path.exists(vector_npy_path):
        with open(meta_json_path, "r", encoding="utf-8") as f:
            documents_meta = json.load(f)
        doc_embeddings = np.load(vector_npy_path, allow_pickle=False)
        doc_embeddings = np.array(doc_embeddings)
        loaded = True
        logger.info("✅ Chatbot vector store loaded (safe JSON/NPY)")

    
    elif os.path.exists(meta_pkl_path) and os.path.exists(vector_pkl_path):
        if settings.allow_unsafe_pickle_load:
            logger.warning(
                "⚠️ Unsafe pickle vector store load enabled. "
                "This is vulnerable to RCE if files are untrusted. Prefer migrating to JSON/NPY."
            )
            with open(meta_pkl_path, "rb") as f:
                documents_meta = pickle.load(f)
            with open(vector_pkl_path, "rb") as f:
                doc_embeddings = pickle.load(f)
                doc_embeddings = np.array(doc_embeddings)
            loaded = True

            try:
                with open(meta_json_path, "w", encoding="utf-8") as f:
                    json.dump(documents_meta, f, ensure_ascii=False)
                np.save(vector_npy_path, doc_embeddings, allow_pickle=False)
                logger.info("✅ Migrated vector store to safe JSON/NPY format")
            except Exception as migrate_err:
                logger.warning(f"Vector store migration skipped/failed: {migrate_err}")
        else:
            logger.error(
                "❌ Vector store is only available as pickle (.pkl) but unsafe pickle loading is disabled. "
                "Run scripts/migrate_vector_store.py to generate vector_meta.json and vector_db.npy."
            )
        
    if loaded:
        logger.info("✅ Vector Database loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load vector database: {e}", exc_info=True)

def expand_query(query: str) -> str:
    replacements = {
        "EIA": "EIA การประเมินผลกระทบสิ่งแวดล้อม Environmental Impact Assessment",
        "GIS": "Geographic Information System",
        "IoT": "Internet of Things",
        "วิชาดิน": "ปฐพีวิทยา ดิน",
        "วิจัย": "ระเบียบวิธีวิจัย",
        "ปี1": "ชั้นปีที่ 1", "ปี 1": "ชั้นปีที่ 1", 
        "ปี2": "ชั้นปีที่ 2", "ปี 2": "ชั้นปีที่ 2", 
        "ปี3": "ชั้นปีที่ 3", "ปี 3": "ชั้นปีที่ 3", 
        "ปี4": "ชั้นปีที่ 4", "ปี 4": "ชั้นปีที่ 4",
        "เทอม1": "ภาคการศึกษาต้น", "เทอม 1": "ภาคการศึกษาต้น", 
        "เทอม2": "ภาคการศึกษาปลาย", "เทอม 2": "ภาคการศึกษาปลาย", 
        "ซัมเมอร์": "ภาคการศึกษาฤดูร้อน"
    }
    for short, full in replacements.items():
        if short.upper() in query.upper():
            query = query + " " + full
    return query

@router.post("/chatbot")
async def get_chatbot_response(req: ChatRequest):
    user_msg = req.message.strip()
    if not user_msg: 
        return {"response": "กรุณาพิมพ์คำถามครับ"}
    
    
    if doc_embeddings is None or embedding_model is None:
        return {"response": "ขออภัยค่ะ ระบบฐานความรู้ AI หรืออินเทอร์เน็ตยังไม่พร้อมใช้งานบนเซิร์ฟเวอร์ค่ะ"}

    try:
        
        search_query = expand_query(user_msg)
        target_code = get_program_code(req.level, req.program)
        
        
        gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not gemini_key:
             return {"response": "พี่ AI ขัดข้องเรื่อง API Key ค่ะ ฝากแจ้งแอดมินทีนะคะ"}

        
        
        
        start_encode_time = time.time()
        
        
        query_embedding = embedding_model.encode([search_query], convert_to_numpy=True)[0]
        encode_duration = time.time() - start_encode_time
        logger.info(f"⏱️ [1] Time to encode vector (Local MiniLM): {encode_duration:.2f} seconds")

        
        
        
        indices = [i for i, m in enumerate(documents_meta) if m.get("program_code") == target_code]
        if not indices:
            return {"response": f"ขออภัยค่ะ ยังไม่มีข้อมูลของหลักสูตร {target_code}"}

        filtered_embeddings = doc_embeddings[indices]
        filtered_meta = [documents_meta[i] for i in indices]

        
        norm_query = np.linalg.norm(query_embedding)
        norm_filtered = np.linalg.norm(filtered_embeddings, axis=1)
        denom = norm_filtered * norm_query
        denom[denom == 0] = 1e-9
        scores = np.dot(filtered_embeddings, query_embedding) / denom
        
        
        top_indices = np.argsort(scores)[::-1][:15]
        
        seen_pages = set()
        final_contexts = []
        
        for idx in top_indices:
            if scores[idx] > 0.20:
                meta = filtered_meta[idx]
                if meta['source'] not in seen_pages:
                    final_contexts.append(f"อ้างอิงจาก {meta['source']}:\n{meta['parent_content']}")
                    seen_pages.add(meta['source'])
            if len(final_contexts) >= 6: break

        
        
        
        if not final_contexts:
            full_context_text = "ไม่มีข้อมูลอ้างอิงจากระบบฐานข้อมูลสำหรับคำถามนี้ (แนะนำให้ตอบกลับอย่างสุภาพ และพยายามสอบถามเพิ่มเติม หรือแจ้งให้ติดต่ออาจารย์)"
        else:
            full_context_text = "\n\n---\n\n".join(final_contexts)
        
        system_prompt = f"""คุณคือ "น้อง NRED" (อ่านว่า เอ็น-เรด) ผู้ช่วยอัจฉริยะสาวสุดน่ารักประจำภาควิชา มหาวิทยาลัยนเรศวร
บุคลิก: น่ารัก สดใส ฉลาด สุภาพ เป็นกันเอง มีอารมณ์ขัน และพร้อมช่วยเหลือเสมอ
หน้าที่: ตอบคำถามและให้คำแนะนำเกี่ยวกับหลักสูตร {target_code}

ลักษณะการพูด (Tone & Style):
- ใช้คำลงท้ายน่ารักๆ เสมอ เช่น "ค่ะ", "นะคะ", "น้า", "จ้า", "ค่า"
- แทนตัวเองว่า "น้อง NRED" 
- "ปรับระดับภาษาให้ล้อตามคู่สนทนา": ถ้าผู้ใช้พิมพ์ทางการ ให้ตอบแบบสุภาพเรียบร้อย ถ้าผู้ใช้พิมพ์เล่น/คุยเป็นกันเอง ให้ตอบกลับแบบน่ารักๆ สดใสเหมือนเพื่อนหรือน้องสาว
- สามารถใช้ Emoji น่ารักๆ ประกอบการสนทนาได้พอประมาณ (เช่น 🌟, 😊, 📚, ✌️, ✨)

กฎเหล็กในการทำงาน:
1. หากมี [ข้อมูลอ้างอิง] ให้ใช้ข้อมูลนั้นเป็นหลักในการตอบคำถาม เพื่อความถูกต้องแม่นยำ
2. หากข้อมูลอ้างอิงเป็นตารางหรือข้อความที่อ่านยาก ให้ย่อยข้อมูลและจัดเรียงเป็นข้อๆ ให้สวยงามและอ่านง่าย
3. หากคำถามเป็นเพียงการทักทาย หรือการคุยเล่นทั่วไป ให้ตอบกลับอย่างเป็นธรรมชาติ สดใส น่ารัก โดยไม่จำเป็นต้องอิงข้อมูลหลักสูตร
4. หากคำถามเกี่ยวกับหลักสูตรแต่ไม่มีในข้อมูลอ้างอิง ให้แจ้งอย่างสุภาพและน่ารักว่าไม่มีข้อมูลในระบบ และแนะนำให้ติดต่ออาจารย์ที่ปรึกษา
5. คิดวิเคราะห์ทีละขั้นตอน (Step-by-step) ก่อนตอบ เพื่อให้คำตอบมีตรรกะและครอบคลุม

[ข้อมูลอ้างอิงสำหรับคำถามปัจจุบัน]
{full_context_text}
"""
        
        
        messages = [{"role": "system", "content": system_prompt}]
        
        
        for h in req.history[-5:]:
            role = "assistant" if h.get("sender") == "bot" else "user"
            msg = h.get("text", "")
            if msg:
                messages.append({"role": role, "content": msg})
        
        
        messages.append({"role": "user", "content": user_msg})
        
        start_gemini_time = time.time()
        
        
        response = await litellm.acompletion(
            model="gemini/gemini-3.1-flash-lite-preview",
            messages=messages,
            api_key=gemini_key,
            temperature=0.3, 
            max_tokens=800
        )
        
        gemini_duration = time.time() - start_gemini_time
        logger.info(f"⏱️ [2] Time waiting for LiteLLM (Gemini): {gemini_duration:.2f} seconds")
        logger.info(f"⏱️ [Total] Response Time: {(encode_duration + gemini_duration):.2f} seconds")

        return {"response": response.choices[0].message.content}
            
    except Exception as e:
        logger.error(f"Chatbot Error: {e}", exc_info=True)
        return {"response": f"เกิดข้อผิดพลาด: {str(e)}"}
