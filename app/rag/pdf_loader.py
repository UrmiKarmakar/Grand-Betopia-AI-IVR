# app/rag/pdf_loader.py
import os
from PyPDF2 import PdfReader

def load_all_pdfs_text(pdf_dir):
    documents = []

    if not os.path.exists(pdf_dir):
        print(f" PDF folder not found: {pdf_dir}")
        return documents

    for file in os.listdir(pdf_dir):
        if file.lower().endswith(".pdf"):
            path = os.path.join(pdf_dir, file)
            print(f" Loading PDF: {file}")

            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            documents.append({
                "text": text.strip(),
                "source": file
            })

    return documents
