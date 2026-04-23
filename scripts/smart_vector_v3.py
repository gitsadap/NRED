import os
import pickle
import numpy as np
try:
    import fitz
except ImportError:
    import pymupdf as fitz
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
docs_dir = os.path.join(base_dir, "docs")
hf_cache_dir = os.path.join(base_dir, "hf_cache")
os.makedirs(hf_cache_dir, exist_ok=True)

print("⏳ Loading AI Embedding Model...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder=hf_cache_dir, device='cpu')

PROGRAM_CODES = ["BS-NRE", "BS-GEO", "MS-NRE", "MS-GISCI", "MS-ENVI", "PHD-NRE", "PHD-ENVI"]

# ใช้ LangChain RecursiveCharacterTextSplitter ซึ่งฉลาดกว่าตัดอักขระดื้อๆ
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=750,
    chunk_overlap=250,
    separators=["\n\n", "\n", " ", ""]
)

documents_meta = []
texts_to_embed = []

print("\n📄 Parsing PDFs and Chunking intelligently with LangChain...")
for root, dirs, files in os.walk(docs_dir):
    for filename in files:
        if filename.endswith(".pdf"):
            file_path = os.path.join(root, filename)
            assigned_code = next((c for c in PROGRAM_CODES if c.upper() in filename.upper()), None)
            if not assigned_code: continue

            print(f"  -> {filename} [Code: {assigned_code}]")
            try:
                doc = fitz.open(file_path)
                for page_num in range(len(doc)):
                    page_text = doc[page_num].get_text("text").strip()
                    if len(page_text) < 50: continue
                    
                    chunks = text_splitter.split_text(page_text)
                    for chunk in chunks:
                        if len(chunk.strip()) > 30:
                            embed_text = f"[{assigned_code}] {chunk.strip()}"
                            texts_to_embed.append(embed_text)
                            documents_meta.append({
                                "program_code": assigned_code,
                                "parent_content": page_text,
                                "source": f"{filename} หน้า {page_num + 1}",
                                "small_fragment": chunk.strip()
                            })
            except Exception as e:
                print(f"Error parsing {filename}: {e}")

if texts_to_embed:
    print(f"\n🧠 Embedding {len(texts_to_embed)} chunks into Vector space...")
    embeddings_numpy = model.encode(texts_to_embed, convert_to_numpy=True, show_progress_bar=True)
    
    with open(os.path.join(hf_cache_dir, "vector_db.pkl"), "wb") as f:
        pickle.dump(embeddings_numpy, f)
    with open(os.path.join(hf_cache_dir, "vector_meta.pkl"), "wb") as f:
        pickle.dump(documents_meta, f)
    print(f"✅ Success! Smart Vector DB rebuilt at {hf_cache_dir}")
