# 🤖 Betopia RAG Chatbot (PDF-based)

A Retrieval-Augmented Generation (RAG) chatbot built in **pure Python** that answers questions **strictly from a PDF document** using:

- OpenAI embeddings
- FAISS vector database
- Short-term conversational memory
- Clean modular architecture

This project demonstrates how RAG works end-to-end, from PDF ingestion to semantic search and memory-aware responses.

## 🚀 Features

- 📄 PDF-based question answering
- 🧠 Semantic search using embeddings
- ⚡ FAISS vector database for fast retrieval
- 🗣️ Conversational memory (last N turns)
- ❌ No hallucinations (answers only from PDF)
- 🧩 Modular, beginner-friendly codebase

Text-unified Multimodal RAG
PDF
 ├── Text pages → text chunks → text embeddings → FAISS (text index)
 └── Images → OCR / Vision → captions → embeddings → FAISS (image index)

User question
 ├── Text retrieval
 ├── Image retrieval
 └── Combined context → GPT-4o → answer

