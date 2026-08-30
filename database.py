import os
import subprocess
import sys
import numpy as np

# Auto-install FAISS if missing, since background terminal pip calls are failing
try:
    import faiss
except ImportError:
    print("Auto-installing faiss-cpu...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "faiss-cpu", "numpy"])
    import faiss

DIMENSION = 384  # Based on all-MiniLM-L6-v2 output

# In-memory FAISS setup
index = faiss.IndexFlatL2(DIMENSION)
metadata_store = []

def init_db():
    """
    Ensure the vector index exists. 
    Using FAISS in-memory so nothing starts up externally.
    """
    print(f"FAISS Local Index Initialized. Dimension: {DIMENSION}")

def upsert_documents(chunks: list[str], embeddings_list: list[list[float]], source_doc: str):
    """
    Store the text chunks and their embeddings into FAISS memory.
    """
    if not embeddings_list:
        return
        
    vectors = np.array(embeddings_list).astype('float32')
    index.add(vectors)
    
    for chunk in chunks:
        metadata_store.append({
            "source": source_doc,
            "text": chunk
        })

def search_similar(query_embedding: list[float], top_k: int = 3):
    """
    Search the FAISS vector DB for the most similar text chunks.
    """
    if index.ntotal == 0:
        return []
        
    query_vector = np.array([query_embedding]).astype('float32')
    distances, indices = index.search(query_vector, top_k)
    
    results = []
    # indices[0] contains the top_k indices
    for i, idx in enumerate(indices[0]):
        if idx != -1 and idx < len(metadata_store):
            meta = metadata_store[idx]
            # Convert L2 distance into a pseudo-similarity score (lower distance = higher similarity)
            similarity = float(1 / (1 + distances[0][i]))
            
            results.append({
                "similarity": similarity,
                "meta": meta
            })
            
    return results
