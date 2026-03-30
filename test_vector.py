import os
import pickle
import torch
from sentence_transformers import SentenceTransformer, util

base_dir = os.path.dirname(os.path.abspath(__file__))
hf_cache_dir = os.path.join(base_dir, "hf_cache")

tensor_path = os.path.join(hf_cache_dir, "vector_db.pt")
meta_path = os.path.join(hf_cache_dir, "vector_meta.pkl")

doc_embeddings = torch.load(tensor_path, weights_only=True)
with open(meta_path, "rb") as f:
    documents_meta = pickle.load(f)

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder=hf_cache_dir, device='cpu')

queries = [
    "ค่าใช้จ่ายตลอดหลักสูตร สาขาภูมิศาสตร์",
    "สาขาทรัพยากรธรรมชาติ เรียนจบไปประกอบอาชีพอะไรได้บ้าง",
    "แผนการศึกษา ปริญญาตรี ภูมิศาสตร์ ปี 1"
]

print("--- DIAGNOSTIC VECTOR RETRIEVAL ---")
for q in queries:
    print(f"\n[QUERY] {q}")
    query_embedding = model.encode(q, convert_to_tensor=True)
    cosine_scores = util.cos_sim(query_embedding, doc_embeddings)[0]
    
    # Simulate filter
    has_geo = "ภูมิศาสตร์" in q
    has_nre = "ธรรมชาติ" in q
    
    for i, meta in enumerate(documents_meta):
        src = meta['source'].lower()
        if has_geo and not has_nre and 'geo' not in src:
            cosine_scores[i] = -1.0
        elif has_nre and not has_geo and 'nre' not in src:
            cosine_scores[i] = -1.0

    topk = torch.topk(cosine_scores, k=3)
    for score, idx in zip(topk.values, topk.indices):
        print(f"  -> [Score: {score.item():.3f} | {documents_meta[idx.item()]['source']}]")
        print(f"     {documents_meta[idx.item()]['content'].replace(chr(10), ' ')}")
        
