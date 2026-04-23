import hashlib
import json
import os
import pickle
from pathlib import Path

import numpy as np


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    hf_cache_dir = base_dir / "hf_cache"

    meta_pkl = hf_cache_dir / "vector_meta.pkl"
    vec_pkl = hf_cache_dir / "vector_db.pkl"

    meta_json = hf_cache_dir / "vector_meta.json"
    vec_npy = hf_cache_dir / "vector_db.npy"

    if not meta_pkl.exists() or not vec_pkl.exists():
        print("❌ Missing pickle files:")
        print(f" - {meta_pkl}")
        print(f" - {vec_pkl}")
        return 1

    print("⚠️ Loading pickle files (only run this script if you trust these files).")
    with meta_pkl.open("rb") as f:
        meta = pickle.load(f)
    with vec_pkl.open("rb") as f:
        embeddings = pickle.load(f)

    embeddings = np.array(embeddings)
    if embeddings.dtype == object:
        print("❌ Embeddings loaded as object dtype; cannot save safely with allow_pickle=False.")
        return 2

    hf_cache_dir.mkdir(exist_ok=True)

    with meta_json.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    np.save(vec_npy, embeddings, allow_pickle=False)

    print("✅ Wrote safe vector store files:")
    print(f" - {meta_json} (sha256={sha256_file(meta_json)})")
    print(f" - {vec_npy} (sha256={sha256_file(vec_npy)})")

    print("\nNext:")
    print(" - Deploy these two files with the app.")
    print(" - Keep ALLOW_UNSAFE_PICKLE_LOAD=False in production.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

