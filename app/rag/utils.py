# app/rag/utils.py
import os, time, hashlib

def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def file_metadata(path: str, version: int):
    return {
        "doc_id": file_hash(path),
        "doc_name": os.path.basename(path),
        "updated_at": int(os.path.getmtime(path)),
        "version": version,
        "priority": version,
    }
