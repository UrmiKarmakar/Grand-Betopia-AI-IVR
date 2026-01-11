# app/rag/sync.py
import os
from typing import List
from .utils import file_hash, load_manifest, save_manifest
from .pdf_loader import load_all_pdfs_text   # your loader: returns list[str] with a header including filename
from .image_reader import load_all_images_text  # returns list[str] including filename
from .chunker import chunk_text
from .embeddings import embed_texts
from .vector_store import create_faiss_index

def gather_files(pdf_dir: str, img_dir: str) -> List[str]:
    files = []
    if os.path.isdir(pdf_dir):
        for fn in os.listdir(pdf_dir):
            if fn.lower().endswith(".pdf"):
                files.append(os.path.join(pdf_dir, fn))
    if os.path.isdir(img_dir):
        for fn in os.listdir(img_dir):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                files.append(os.path.join(img_dir, fn))
    return sorted(files)

def build_documents_list(pdf_dir: str, img_dir: str, client=None) -> list:
    """
    Return list of document texts. Each element should include a source marker, e.g.
    "[PDF: filename.pdf]\n<text...>" or "[Image: name.png]\n<text...>"
    This uses your existing loaders.
    """
    pdf_texts = load_all_pdfs_text(pdf_dir)  # returns list of strings like "[PDF: fname]\ntext"
    image_texts = load_all_images_text(img_dir, client)  # same pattern
    return pdf_texts + image_texts

def sync_and_rebuild(pdf_dir: str, img_dir: str, client) -> bool:
    """
    Check manifest for changes. If changed, rebuild entire FAISS index.
    Returns True if rebuild happened.
    """
    manifest = load_manifest()
    files = gather_files(pdf_dir, img_dir)
    changed = False

    current_map = {}
    for f in files:
        try:
            current_map[f] = file_hash(f)
        except Exception:
            current_map[f] = None

    # detect any differences or deletions
    # if manifest keys differ or any file hash changed -> changed True
    if set(manifest.keys()) != set(current_map.keys()):
        changed = True
    else:
        for k in current_map:
            if manifest.get(k) != current_map.get(k):
                changed = True
                break

    if not changed:
        return False

    # Save new manifest
    save_manifest(current_map)

    # Rebuild index from scratch
    docs = build_documents_list(pdf_dir, img_dir, client)
    # chunk each doc and attach metadata
    all_chunks = []
    metadatas = []
    for doc_text in docs:
        # you may want to add a doc_id and source in metadata
        # assume doc_text starts with [PDF: filename] or [Image: filename]
        header = ""
        if "\n" in doc_text:
            header, body = doc_text.split("\n", 1)
        else:
            header, body = "", doc_text

        chunks = chunk_text(body)
        for c in chunks:
            all_chunks.append(c)
            metadatas.append({
                "source_header": header,
                "text_preview": c[:200]
            })

    # embed
    embeddings = embed_texts(all_chunks)
    # create index and save
    create_faiss_index(embeddings, all_chunks, metadatas)
    return True
