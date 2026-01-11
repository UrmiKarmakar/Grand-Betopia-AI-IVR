# app/rag/upload_manager.py
import os
import shutil
import time
from PyPDF2 import PdfReader

from .image_loader import image_to_text
from .chunker import chunk_text
from .embeddings import embed_texts
from .vector_store import create_faiss_index

SUPPORTED_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
SUPPORTED_DOC_EXT = (".pdf",) + SUPPORTED_IMAGE_EXT

def ensure_tmp_dir(tmp_dir: str):
    os.makedirs(tmp_dir, exist_ok=True)

def save_uploaded_files(tmp_dir: str, paths: list) -> list:
    """Copy user files into tmp_dir for runtime session."""
    ensure_tmp_dir(tmp_dir)
    saved = []
    for src in paths:
        if not os.path.isfile(src):
            print(f" Skipped (not a file): {src}")
            continue
        if not src.lower().endswith(SUPPORTED_DOC_EXT):
            print(f" Skipped (unsupported type): {src}")
            continue
        dst = os.path.join(tmp_dir, os.path.basename(src))
        shutil.copy2(src, dst)
        saved.append(dst)
    return saved

def load_text_from_file(path: str, client) -> dict:
    """Return {'text': ..., 'source': filename, 'type': 'upload'}."""
    filename = os.path.basename(path)
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return {"text": text.strip(), "source": filename, "type": "upload"}
    elif filename.lower().endswith(SUPPORTED_IMAGE_EXT):
        text = image_to_text(path, client)
        return {"text": text, "source": filename, "type": "upload"}
    else:
        raise ValueError(f"Unsupported file type: {filename}")

def build_temp_index(tmp_dir: str, client):
    """Build FAISS index from files in tmp_dir."""
    if not os.path.isdir(tmp_dir):
        return None

    docs = []
    for fn in os.listdir(tmp_dir):
        path = os.path.join(tmp_dir, fn)
        if os.path.isfile(path) and fn.lower().endswith(SUPPORTED_DOC_EXT):
            print(f" Upload indexed: {fn}")
            docs.append(load_text_from_file(path, client))

    if not docs:
        return None

    timestamp = int(time.time())
    chunks, metadatas = [], []
    for doc in docs:
        doc_chunks = chunk_text(doc["text"])
        chunks.extend(doc_chunks)
        metadatas.extend([{
            "source": doc["source"],
            "type": doc["type"],
            "updated_at": timestamp
        }] * len(doc_chunks))

    vectors = embed_texts(chunks)
    index = create_faiss_index(vectors=vectors, texts=chunks, metadatas=metadatas)
    return index

def clear_tmp_dir(tmp_dir: str):
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
