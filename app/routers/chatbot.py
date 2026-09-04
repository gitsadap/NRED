import os
import pickle
import json
import time
import hashlib
import numpy as np
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
import pydantic
from pydantic import BaseModel
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_LOG_LEVEL"] = "ERROR"
import litellm
from app.logging_config import logger
from typing import List, Dict, Optional
from app.config import settings
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------------------------
# โหลด Embedding Model
# ---------------------------------------------------------------------------
try:
    embedding_model = SentenceTransformer(
        'paraphrase-multilingual-MiniLM-L12-v2',
        cache_folder="hf_cache",
        local_files_only=True,
    )
except Exception as e:
    logger.error(f"❌ Failed to load SentenceTransformer (local): {e}")
    try:
        embedding_model = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2',
            cache_folder="hf_cache",
        )
    except Exception as e2:
        logger.error(f"❌ Fallback load failed: {e2}")
        embedding_model = None

router = APIRouter(prefix="/api/v1", tags=["Chatbot AI"])


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    level: Optional[str] = None
    program: Optional[str] = None


# ---------------------------------------------------------------------------
# Program code mapping
# ---------------------------------------------------------------------------
def get_program_code(level: str, program: str) -> Optional[str]:
    mapping = {
        ("ปริญญาตรี",  "ทรัพยากรธรรมชาติและสิ่งแวดล้อม (NRE)"): "BS-NRE",
        ("ปริญญาตรี",  "ภูมิศาสตร์ (GEO)"):                      "BS-GEO",
        ("ปริญญาโท",   "ทรัพยากรธรรมชาติและสิ่งแวดล้อม (NRE)"): "MS-NRE",
        ("ปริญญาโท",   "ภูมิสารสนเทศ (GISCI)"):                  "MS-GISCI",
        ("ปริญญาโท",   "วิทยาศาสตร์สิ่งแวดล้อม (ENVI)"):        "MS-ENVI",
        ("ปริญญาเอก",  "ทรัพยากรธรรมชาติและสิ่งแวดล้อม (NRE)"): "PHD-NRE",
        ("ปริญญาเอก",  "วิทยาศาสตร์สิ่งแวดล้อม (ENVI)"):        "PHD-ENVI",
    }
    return mapping.get((level, program))


# ---------------------------------------------------------------------------
# โหลด Vector Database
# ---------------------------------------------------------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
hf_cache_dir = os.path.join(base_dir, "hf_cache")

doc_embeddings = None
documents_meta = []

try:
    meta_json_path  = os.path.join(hf_cache_dir, "vector_meta.json")
    vector_npy_path = os.path.join(hf_cache_dir, "vector_db.npy")
    meta_pkl_path   = os.path.join(hf_cache_dir, "vector_meta.pkl")
    vector_pkl_path = os.path.join(hf_cache_dir, "vector_db.pkl")

    loaded = False

    if os.path.exists(meta_json_path) and os.path.exists(vector_npy_path):
        with open(meta_json_path, "r", encoding="utf-8") as f:
            documents_meta = json.load(f)
        doc_embeddings = np.load(vector_npy_path, allow_pickle=False)
        doc_embeddings = np.array(doc_embeddings, dtype=np.float32)
        loaded = True
        logger.info("✅ Chatbot vector store loaded (safe JSON/NPY)")

    elif os.path.exists(meta_pkl_path) and os.path.exists(vector_pkl_path):
        if settings.allow_unsafe_pickle_load:
            logger.warning("⚠️ Loading vector store from pickle (unsafe). Migrate to JSON/NPY.")
            with open(meta_pkl_path, "rb") as f:
                documents_meta = pickle.load(f)
            with open(vector_pkl_path, "rb") as f:
                doc_embeddings = np.array(pickle.load(f), dtype=np.float32)
            loaded = True
            try:
                with open(meta_json_path, "w", encoding="utf-8") as f:
                    json.dump(documents_meta, f, ensure_ascii=False)
                np.save(vector_npy_path, doc_embeddings, allow_pickle=False)
                logger.info("✅ Migrated vector store → JSON/NPY")
            except Exception as me:
                logger.warning(f"Migration skipped: {me}")
        else:
            logger.error("❌ Pickle vector store disabled. Run scripts/migrate_vector_store.py")

    if loaded:
        logger.info(f"✅ Vector DB loaded: {len(documents_meta)} chunks")
except Exception as e:
    logger.error(f"❌ Failed to load vector database: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# 🆕 FEATURE 1: Query Result Cache (TTL-based)
# ---------------------------------------------------------------------------
_search_cache: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 300  # 5 นาที
MAX_CACHE_SIZE = 300


def _cache_key(query: str, code: Optional[str]) -> str:
    raw = f"{query.strip().lower()}|{code or ''}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _get_cached(query: str, code: Optional[str]):
    key = _cache_key(query, code)
    entry = _search_cache.get(key)
    if entry:
        ts, result = entry
        if datetime.now() - ts < timedelta(seconds=CACHE_TTL_SECONDS):
            return result
        del _search_cache[key]
    return None


def _set_cache(query: str, code: Optional[str], result) -> None:
    key = _cache_key(query, code)
    _search_cache[key] = (datetime.now(), result)
    if len(_search_cache) > MAX_CACHE_SIZE:
        now = datetime.now()
        ttl = timedelta(seconds=CACHE_TTL_SECONDS)
        expired = [k for k, (ts, _) in _search_cache.items() if now - ts > ttl]
        for k in expired:
            del _search_cache[k]


# ---------------------------------------------------------------------------
# 🆕 FEATURE 2: Dynamic Similarity Threshold
# ---------------------------------------------------------------------------
def _dynamic_threshold(query: str) -> float:
    """
    ยิ่งคำถามยาว/เฉพาะเจาะจง → ยิ่งลด threshold ได้
    ยิ่งคำถามสั้น/คลุมเครือ → ต้องการความมั่นใจสูงขึ้น
    """
    n = len(query.strip())
    if n <= 5:
        return 0.30
    elif n <= 15:
        return 0.25
    elif n <= 60:
        return 0.20
    else:
        return 0.15


# ---------------------------------------------------------------------------
# 🆕 FEATURE 3: Keyword Reranker
# ---------------------------------------------------------------------------
_TH_STOPWORDS = {
    'ใน', 'ของ', 'และ', 'ที่', 'ให้', 'มี', 'การ', 'เป็น', 'จาก',
    'กับ', 'ได้', 'ว่า', 'แล้ว', 'ไม่', 'นี้', 'จะ', 'ถ้า', 'หรือ',
    'เพื่อ', 'โดย', 'แต่', 'ก็', 'ซึ่ง', 'อย่าง', 'เมื่อ', 'ต้อง',
    'ผ่าน', 'ทั้ง', 'ตาม', 'อื่น', 'ๆ',
}

_SECTION_KEYWORDS = [
    'รายวิชา', 'โครงสร้าง', 'หลักสูตร', 'แผนการ', 'เกณฑ์',
    'คุณสมบัติ', 'วัตถุประสงค์', 'หน่วยกิต', 'ชั้นปี', 'ภาคการศึกษา',
    'บังคับ', 'เลือก', 'วิชาแกน', 'วิทยานิพนธ์', 'สหกิจ',
]


def _keyword_rerank(
    query: str,
    filtered_meta: list,
    scores: np.ndarray,
    top_indices: np.ndarray,
) -> list:
    """
    Rerank top cosine-similarity results โดยบวก bonus คะแนนจาก:
    - Keyword overlap ระหว่าง query กับ chunk
    - การมี section keywords สำคัญใน chunk
    """
    query_words = set(query.lower().split()) - _TH_STOPWORDS
    query_words = {w for w in query_words if len(w) > 1}

    reranked = []
    for idx in top_indices:
        base_score = float(scores[idx])
        chunk_text = (
            filtered_meta[idx].get('small_fragment', '') + ' ' +
            filtered_meta[idx].get('parent_content', '')[:600]
        ).lower()

        # Keyword overlap boost (+0.02 per matched word, max 0.10)
        matched = sum(1 for w in query_words if w in chunk_text)
        keyword_boost = min(matched * 0.02, 0.10)

        # Section header boost (+0.01 per term, max 0.05)
        section_boost = min(
            sum(0.01 for t in _SECTION_KEYWORDS if t in chunk_text),
            0.05,
        )

        reranked.append((idx, base_score + keyword_boost + section_boost))

    reranked.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in reranked]


# ---------------------------------------------------------------------------
# Query Expansion
# ---------------------------------------------------------------------------
def expand_query(query: str) -> str:
    replacements = {
        "EIA":    "EIA การประเมินผลกระทบสิ่งแวดล้อม Environmental Impact Assessment",
        "GIS":    "GIS Geographic Information System ภูมิสารสนเทศ",
        "RS":     "RS Remote Sensing การรับรู้จากระยะไกล",
        "IoT":    "IoT Internet of Things",
        "วิชาดิน": "ปฐพีวิทยา ดิน",
        "วิจัย":  "ระเบียบวิธีวิจัย",
        "ปี1":    "ชั้นปีที่ 1", "ปี 1": "ชั้นปีที่ 1",
        "ปี2":    "ชั้นปีที่ 2", "ปี 2": "ชั้นปีที่ 2",
        "ปี3":    "ชั้นปีที่ 3", "ปี 3": "ชั้นปีที่ 3",
        "ปี4":    "ชั้นปีที่ 4", "ปี 4": "ชั้นปีที่ 4",
        "เทอม1":  "ภาคการศึกษาต้น",  "เทอม 1": "ภาคการศึกษาต้น",
        "เทอม2":  "ภาคการศึกษาปลาย", "เทอม 2": "ภาคการศึกษาปลาย",
        "ซัมเมอร์": "ภาคการศึกษาฤดูร้อน",
    }
    for short, full in replacements.items():
        if short.upper() in query.upper():
            query = query + " " + full
    return query


# ---------------------------------------------------------------------------
# Core vector search (runs in threadpool)
# ---------------------------------------------------------------------------
def _vector_search(query: str, code: Optional[str]):
    """
    คืนค่า (encode_duration, filtered_meta, scores, top_indices)
    หรือ (encode_duration, None, None, None) ถ้าไม่มีข้อมูล
    """
    t0 = time.time()
    query_emb = embedding_model.encode([query], convert_to_numpy=True)[0].astype(np.float32)
    encode_duration = time.time() - t0

    # กรองตาม program_code (None = ค้นทุก code)
    if code:
        idx_list = [i for i, m in enumerate(documents_meta) if m.get("program_code") == code]
    else:
        idx_list = list(range(len(documents_meta)))

    if not idx_list:
        return encode_duration, None, None, None

    f_emb  = doc_embeddings[idx_list]
    f_meta = [documents_meta[i] for i in idx_list]

    # Cosine similarity
    n_q = np.linalg.norm(query_emb)
    n_d = np.linalg.norm(f_emb, axis=1)
    denom = n_d * n_q
    denom[denom == 0] = 1e-9
    scores = np.dot(f_emb, query_emb) / denom

    top_indices = np.argsort(scores)[::-1][:15]
    return encode_duration, f_meta, scores, top_indices


# ---------------------------------------------------------------------------
# Chatbot endpoint
# ---------------------------------------------------------------------------
@router.post("/chatbot")
async def get_chatbot_response(req: ChatRequest):
    user_msg = req.message.strip()
    if not user_msg:
        return {"response": "กรุณาพิมพ์คำถามครับ"}

    if doc_embeddings is None or embedding_model is None:
        return {"response": "ขออภัยค่ะ ระบบฐานความรู้ AI ยังไม่พร้อมใช้งานค่ะ"}

    try:
        search_query = expand_query(user_msg)
        target_code  = get_program_code(req.level, req.program) if req.level and req.program else None

        gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            return {"response": "พี่ AI ขัดข้องเรื่อง API Key ค่ะ ฝากแจ้งแอดมินทีนะคะ"}

        # ─── 🆕 ตรวจ Cache ก่อน ────────────────────────────────────────────
        cached_contexts = _get_cached(search_query, target_code)
        encode_duration = 0.0

        if cached_contexts is not None:
            final_contexts = cached_contexts
            logger.info("⚡ Cache hit — skipping vector search")
        else:
            # ─── Vector Search (threadpool) ──────────────────────────────────
            from fastapi.concurrency import run_in_threadpool
            encode_duration, filtered_meta, scores, top_indices = await run_in_threadpool(
                _vector_search, search_query, target_code
            )
            logger.info(f"⏱️ [1] Encode: {encode_duration:.2f}s")

            # ─── Fallback: ถ้าไม่พบข้อมูลหลักสูตร → ลองค้น FACULTY ──────────
            if filtered_meta is None:
                if target_code:
                    # มีการเลือกหลักสูตร แต่ไม่มี chunk → ลอง FACULTY
                    logger.info(f"No chunks for {target_code}, falling back to FACULTY search")
                    encode_duration, filtered_meta, scores, top_indices = _vector_search(
                        search_query, "FACULTY"
                    )
                    if filtered_meta is None:
                        return {"response": f"ขออภัยค่ะ ยังไม่มีข้อมูลของหลักสูตร {target_code} ในระบบค่ะ"}
                else:
                    # ไม่ได้เลือกหลักสูตร → ค้นหาใน FACULTY
                    logger.info("No program selected, searching FACULTY index")
                    encode_duration, filtered_meta, scores, top_indices = _vector_search(
                        search_query, "FACULTY"
                    )
                    if filtered_meta is None:
                        return {"response": "ขออภัยค่ะ ยังไม่พบข้อมูลที่เกี่ยวข้องค่ะ ลองถามใหม่หรือเลือกหลักสูตรก่อนนะคะ 😊"}

            # ─── 🆕 Keyword Reranker ─────────────────────────────────────────
            if filtered_meta is not None:
                reranked_indices = _keyword_rerank(user_msg, filtered_meta, scores, top_indices)
            else:
                reranked_indices = []

            # ─── 🆕 Dynamic Threshold ────────────────────────────────────────
            threshold = _dynamic_threshold(user_msg)
            logger.info(f"🎯 Dynamic threshold: {threshold:.2f} (query len={len(user_msg)})")

            seen_pages    = set()
            final_contexts = []
            for idx in reranked_indices:
                if scores[idx] > threshold:
                    meta = filtered_meta[idx]
                    src  = meta['source']
                    if src not in seen_pages:
                        final_contexts.append(
                            f"อ้างอิงจาก {src}:\n{meta['parent_content']}"
                        )
                        seen_pages.add(src)
                if len(final_contexts) >= 6:
                    break

            # ─── บันทึก Cache ────────────────────────────────────────────────
            _set_cache(search_query, target_code, final_contexts)

        # ─── สร้าง Context Text ───────────────────────────────────────────
        if not final_contexts:
            full_context_text = (
                "ไม่มีข้อมูลอ้างอิงจากระบบฐานข้อมูลสำหรับคำถามนี้ "
                "(แนะนำให้ตอบกลับอย่างสุภาพ และพยายามสอบถามเพิ่มเติม "
                "หรือแจ้งให้ติดต่ออาจารย์)"
            )
        else:
            full_context_text = "\n\n---\n\n".join(final_contexts)

        # ─── System Prompt ────────────────────────────────────────────────
        system_prompt = f"""คุณคือ "น้อง NRED" (อ่านว่า เอ็น-เรด) ผู้ช่วยอัจฉริยะสาวสุดน่ารักประจำภาควิชา มหาวิทยาลัยนเรศวร
บุคลิก: น่ารัก สดใส ฉลาด สุภาพ เป็นกันเอง มีอารมณ์ขัน และพร้อมช่วยเหลือเสมอ
หน้าที่: ตอบคำถามและให้คำแนะนำเกี่ยวกับหลักสูตร {target_code or "ของภาควิชา NRED"}

ลักษณะการพูด (Tone & Style):
- ใช้คำลงท้ายน่ารักๆ เสมอ เช่น "ค่ะ", "นะคะ", "น้า", "จ้า", "ค่า"
- แทนตัวเองว่า "น้อง NRED"
- ปรับระดับภาษาให้ล้อตามคู่สนทนา: ทางการ → สุภาพ, เป็นกันเอง → น่ารักสดใส
- สามารถใช้ Emoji น่ารักๆ ประกอบการสนทนาได้พอประมาณ (🌟, 😊, 📚, ✌️, ✨)

กฎเหล็กในการทำงาน:
1. หากมี [ข้อมูลอ้างอิง] ให้ใช้ข้อมูลนั้นเป็นหลัก เพื่อความถูกต้องแม่นยำ
2. หากข้อมูลอ้างอิงเป็นตารางหรือข้อความที่อ่านยาก ให้ย่อยและจัดเรียงเป็นข้อๆ ให้สวยงาม
3. หากคำถามเป็นการทักทายหรือคุยเล่นทั่วไป ให้ตอบกลับอย่างเป็นธรรมชาติ สดใส น่ารัก
4. หากคำถามเกี่ยวกับหลักสูตรแต่ไม่มีในข้อมูลอ้างอิง ให้แจ้งอย่างสุภาพและแนะนำให้ติดต่ออาจารย์
5. คิดวิเคราะห์ทีละขั้นตอน (Step-by-step) ก่อนตอบ เพื่อให้คำตอบมีตรรกะและครอบคลุม

[ข้อมูลอ้างอิงสำหรับคำถามปัจจุบัน]
{full_context_text}
"""

        # ─── Build Messages ───────────────────────────────────────────────
        messages = [{"role": "system", "content": system_prompt}]
        for h in req.history[-5:]:
            sender = h.get("sender") or h.get("role")
            role   = "assistant" if sender in ["bot", "ai", "assistant"] else "user"
            msg    = h.get("text") or h.get("content", "")
            if msg:
                messages.append({"role": role, "content": msg})
        messages.append({"role": "user", "content": user_msg})

        # ─── LLM Call (retry + exponential backoff) ───────────────────────
        # 🔧 แก้ไข model names ที่ typo (gemini-3.1-flash-lite-preview ไม่มีจริง)
        models_to_try = [
            "gemini/gemini-2.0-flash-lite",  # เร็ว ประหยัด
            "gemini/gemini-2.5-flash",        # ฉลาดกว่า ใช้เป็น fallback
            "gemini/gemini-2.0-flash-lite",
            "gemini/gemini-2.5-flash",
        ]

        import asyncio
        t_llm   = time.time()
        response    = None
        last_error  = None
        retry_delay = 1.5

        for attempt, model in enumerate(models_to_try):
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    api_key=gemini_key,
                    temperature=0.3,
                    max_tokens=2048,
                )
                break
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} ({model}) failed: {e}")
                if attempt < len(models_to_try) - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5

        llm_duration = time.time() - t_llm
        logger.info(f"⏱️ [2] LLM: {llm_duration:.2f}s | total: {encode_duration + llm_duration:.2f}s")

        if not response:
            err = str(last_error).lower()
            if any(k in err for k in ("rate limit", "429", "quota")):
                return {"response": "ขออภัยค่ะ ตอนนี้ระบบ AI มีผู้ใช้งานเยอะจนโควต้าเต็มชั่วคราว รบกวนทิ้งช่วงสัก 1-2 นาทีแล้วลองใหม่นะคะ 🙏"}
            return {"response": f"ขออภัยค่ะ ระบบ AI เชื่อมต่อขัดข้องชั่วคราว ({type(last_error).__name__}) รบกวนลองใหม่อีกครั้งนะคะ 🙏"}

        return {"response": response.choices[0].message.content}

    except Exception as e:
        logger.error(f"Chatbot Error: {e}", exc_info=True)
        return {"response": f"เกิดข้อผิดพลาด: {str(e)}"}
