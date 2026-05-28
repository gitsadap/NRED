import pickle
import numpy as np

with open("hf_cache/vector_db.pkl", "rb") as f:
    db = pickle.load(f)
print(f"Type: {type(db)}")
if isinstance(db, np.ndarray):
    print(f"Shape: {db.shape}")
elif isinstance(db, list) and len(db) > 0:
    print(f"Length: {len(db)}, Dim 0 shape: {np.array(db[0]).shape}")
