# app/rag/image_reader.py
import os
from .image_loader import image_to_text

SUPPORTED_EXT = (".png", ".jpg", ".jpeg", ".webp")

def load_all_images_text(image_dir, client):
    documents = []

    if not os.path.exists(image_dir):
        return documents

    for file in os.listdir(image_dir):
        if file.lower().endswith(SUPPORTED_EXT):
            path = os.path.join(image_dir, file)
            print(f" Loading image: {file}")

            text = image_to_text(path, client)

            documents.append({
                "text": text,
                "source": file
            })

    return documents
