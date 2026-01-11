# app/rag/retriever.py
import numpy as np

def retrieve_chunks(query, index, embed_func, top_k=5):
    q_vec = embed_func(query)[0].astype("float32")

    D, I = index["faiss"].search(
        np.array([q_vec]),
        top_k
    )

    results = []
    for idx in I[0]:
        results.append({
            "text": index["texts"][idx],
            "metadata": index["metadatas"][idx]
        })

    return results

