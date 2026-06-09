import json
import os
import time

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hf_cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cached_data(key, max_age=86400):
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < max_age:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return None

def set_cached_data(key, data):
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass
