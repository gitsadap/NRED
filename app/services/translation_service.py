import hashlib
import json
import re
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

SUPPORTED_LANGS = {
    "en": "English",
    "zh": "Simplified Chinese (Mandarin)",
    "ja": "Japanese"
}

def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


async def translate_texts(texts: List[str], target_lang: str, db: AsyncSession) -> List[str]:
    """Translate a list of texts to target_lang using DB cache + Gemini fallback."""
    if target_lang == "th" or target_lang not in SUPPORTED_LANGS:
        return texts

    results = list(texts)
    hashes = [_hash(t) for t in texts]

    # --- Batch fetch from DB cache ---
    cached_rows = await db.execute(
        text("""
            SELECT text_hash, translated_text
            FROM api.translations
            WHERE lang = :lang AND text_hash = ANY(:hashes)
        """),
        {"lang": target_lang, "hashes": hashes}
    )
    cache_map = {row.text_hash: row.translated_text for row in cached_rows}

    # Identify uncached texts
    uncached_indices = [i for i, h in enumerate(hashes) if h not in cache_map]
    uncached_texts = [texts[i] for i in uncached_indices]

    # Fill cached results
    for i, h in enumerate(hashes):
        if h in cache_map:
            results[i] = cache_map[h]

    if not uncached_texts:
        return results

    # --- Call Gemini to translate ---
    lang_name = SUPPORTED_LANGS[target_lang]
    prompt = (
        f"Translate each item in the JSON array below from Thai to {lang_name}. "
        f"Return ONLY a valid JSON array of translated strings in the exact same order. "
        f"Preserve formatting, numbers, URLs, and proper nouns as-is.\n\n"
        f"Input: {json.dumps(uncached_texts, ensure_ascii=False)}"
    )

    translated_texts = uncached_texts  # fallback
    try:
        import litellm
        from app.config import settings
        gemini_key = settings.gemini_api_key or ""
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.1,
            api_key=gemini_key or None
        )
        content = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) == len(uncached_texts):
            translated_texts = [str(t) for t in parsed]
    except Exception as e:
        print(f"[Translation] Gemini error: {e}")

    # --- Save new translations to DB ---
    try:
        for orig, trans in zip(uncached_texts, translated_texts):
            h = _hash(orig)
            await db.execute(
                text("""
                    INSERT INTO api.translations (text_hash, lang, original_text, translated_text)
                    VALUES (:hash, :lang, :orig, :trans)
                    ON CONFLICT (text_hash, lang) DO NOTHING
                """),
                {"hash": h, "lang": target_lang, "orig": orig, "trans": trans}
            )
        await db.commit()
    except Exception as e:
        print(f"[Translation] DB save error: {e}")

    # Fill results
    for i, trans in zip(uncached_indices, translated_texts):
        results[i] = trans

    return results
