# app/rag/ingest.py
import os
from pathlib import Path
import PyPDF2
from app.rag.embeddings import embed_texts
from app.rag.vector_store import create_faiss_index, save_faiss_index

# Paths setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PDF_DIR = BASE_DIR / "data" / "pdf"
DATA_DIR = BASE_DIR / "data"

def extract_text_from_pdf(pdf_path):
    """Helper function to extract all text from a PDF file."""
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f" Could not read {pdf_path.name}: {e}")
    return text

def run_ingestion():
    all_vectors = []
    all_texts = []
    all_metadatas = []
    
    # Check if PDF directory exists
    if not PDF_DIR.exists():
        print(f" PDF folder not found at: {PDF_DIR}")
        return

    print(f" Scanning for PDFs in {PDF_DIR}...")
    pdf_files = list(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(" No PDF files found in data/pdf/.")
        return

    for pdf_path in pdf_files:
        print(f" Processing: {pdf_path.name}")
        content = extract_text_from_pdf(pdf_path)
        
        if content.strip():
            # Chunking logic: 1500 chars with 300 char overlap
            text_chunks = [content[i:i+1500] for i in range(0, len(content), 1200)]
            
            # Generate embeddings for these chunks via your embeddings.py
            chunk_vectors = embed_texts(text_chunks)
            
            for i, chunk_text in enumerate(text_chunks):
                all_vectors.append(chunk_vectors[i])
                all_texts.append(chunk_text)
                all_metadatas.append({"source": pdf_path.name, "chunk": i})

    if not all_vectors:
        print(" No text extracted from PDFs.")
        return

    # 1. Create the index bundle (Returns dictionary with faiss, texts, metadatas)
    print(f" Creating search index for {len(all_texts)} segments...")
    index_bundle = create_faiss_index(all_vectors, all_texts, all_metadatas)

    # 2. Save the index and pickle metadata using your save_faiss_index function
    # Note: DATA_DIR must exist
    DATA_DIR.mkdir(exist_ok=True)
    
    index_path = str(DATA_DIR / "hotel_knowledge.bin")
    meta_path = str(DATA_DIR / "hotel_metadata.json") # Your vector_store uses pickle, this name is fine.
    
    save_faiss_index(index_bundle, index_path, meta_path)
    
    print(f"\n SUCCESS! Knowledge base is ready for Alex.")

if __name__ == "__main__":
    run_ingestion()