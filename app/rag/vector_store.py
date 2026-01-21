# app/rag/vector_store.py
import faiss
import numpy as np
import pickle
import os

def create_faiss_index(vectors, texts, metadatas):
    """
    Creates a high-speed search index.
    """
    if not vectors:
        raise ValueError("No vectors provided. Please check your PDF/Image folders.")

    dim = len(vectors[0])
    # IndexFlatL2 is accurate for small-to-medium sized datasets.
    index = faiss.IndexFlatL2(dim)
    index.add(np.vstack(vectors).astype("float32"))

    return {
        "faiss": index,
        "texts": texts,
        "metadatas": metadatas
    }

def save_faiss_index(index_bundle, index_path, meta_path):
    """
    Saves the mathematical index and text data to disk.
    """
    # 1. Save the FAISS index (the math part)
    faiss.write_index(index_bundle["faiss"], index_path)
    
    # 2. Save the texts and metadatas (the human part) using pickle
    with open(meta_path, "wb") as f:
        pickle.dump({
            "texts": index_bundle["texts"],
            "metadatas": index_bundle["metadatas"]
        }, f)
    print(f" Knowledge base cached to {index_path}")

def load_faiss_index(index_path, meta_path):
    """
    Loads the knowledge base from disk so you don't have to re-process PDFs/Images.
    """
    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        return None

    # 1. Load the FAISS index
    index = faiss.read_index(index_path)
    
    # 2. Load the texts and metadatas
    with open(meta_path, "rb") as f:
        data = pickle.load(f)
        
    return {
        "faiss": index,
        "texts": data["texts"],
        "metadatas": data["metadatas"]
    }