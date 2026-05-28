import numpy as np

try:
    db = np.load("hf_cache/vector_db.npy")
    print(f"NPY Shape: {db.shape}")
except Exception as e:
    print(e)
