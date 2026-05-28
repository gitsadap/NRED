import json
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
hf_cache_dir = os.path.join(base_dir, "hf_cache")
meta_json_path = os.path.join(hf_cache_dir, "vector_meta.json")

if os.path.exists(meta_json_path):
    with open(meta_json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print(f"Total entries: {len(meta)}")
    programs = set(m.get("program_code") for m in meta)
    print(f"Programs found: {programs}")
else:
    print("meta.json not found")
