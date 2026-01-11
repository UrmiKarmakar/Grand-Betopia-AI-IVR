# app/rag/vector_store.py
import faiss
import numpy as np

def create_faiss_index(vectors, texts, metadatas):
    if not vectors:
        raise ValueError("No vectors provided")

    dim = len(vectors[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.vstack(vectors).astype("float32"))  # stack vectors

    return {
        "faiss": index,
        "texts": texts,
        "metadatas": metadatas
    }
