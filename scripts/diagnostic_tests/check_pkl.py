import pickle
import os

hf_cache_dir = "hf_cache"
meta_pkl_path = os.path.join(hf_cache_dir, "vector_meta.pkl")

if os.path.exists(meta_pkl_path):
    with open(meta_pkl_path, "rb") as f:
        meta = pickle.load(f)
    print(f"Total entries in PKL: {len(meta)}")
    programs = set(m.get("program_code") for m in meta)
    print(f"Programs found in PKL: {programs}")
else:
    print("meta.pkl not found")
