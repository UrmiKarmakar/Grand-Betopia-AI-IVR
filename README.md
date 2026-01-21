# Grand Betopia AI Concierge (IVR System)
An enterprise-grade, AI-driven Interactive Voice Response (IVR) backend designed for the **Grand Betopia Hotel**. This system leverages **Retrieval-Augmented Generation (RAG)** and **OpenAI Function Calling** to automate guest inquiries, room availability checks, and reservation management.

## 📖 Overview
The Grand Betopia AI Concierge acts as a sophisticated digital front desk. Unlike traditional IVR systems that rely on rigid DTMF (key-press) menus, this system uses Natural Language Processing (NLP) to understand guest intent, retrieve real-time hotel data, and execute transactions directly into the hotel's database.

### The Purpose
* **Automate Bookings**: Reduce front-desk workload by handling end-to-end reservations.
* **Instant Information**: Provide accurate answers regarding hotel policies, amenities, and pricing using an indexed knowledge base.
* **Seamless Integration**: Synchronize data between a relational SQLite database and modern JSON-based management exports.

## 🏗️ System Architecture
The system is built on a modular architecture to ensure scalability and reliability:

1. **The Intelligence Layer (OpenAI GPT-4o)**: Functions as the core logic engine, managing conversation flow and decision-making.
2. **The Knowledge Layer (RAG & FAISS)**: A vector database that stores hotel-specific documents. When a guest asks a question, the system retrieves the most relevant "chunks" of data to provide an accurate, non-hallucinated answer.
3. **The Action Layer (Function Calling)**: Bridges the gap between conversation and data. The AI can "call" Python functions to query the database or save guest information.
4. **The Persistence Layer (SQLite & JSON)**:
* **SQLite**: Stores relational data for Users, Services, and Bookings.
* **JSON**: Generates individual confirmation receipts for every transaction.

## 🛠️ Key Features
* **Natural Language Date Parsing**: Supports flexible date inputs (e.g., "next Tuesday," "Jan 22nd," "the day after tomorrow") and standardizes them to ISO format for 2026.
* **Overlap Prevention**: The booking logic contains a strict validation engine to ensure rooms cannot be double-booked for the same dates.
* **Dynamic Pricing**: Calculates total stay costs based on the number of nights and specific room rates.
* **Professional Persona**: The "Alex" concierge persona is tuned for high-end hospitality, ensuring a formal and attentive tone.

## 📂 Project Structure

Hotel IVR/
├── app/
│   ├── main.py                # Main execution loop and Tool Routing
│   ├── database/
│   │   ├── db_manager.py      # SQLite schema, Seeding, and CRUD operations
│   │   └── __init__.py
│   └── rag/
│       ├── actions.py         # Business logic for booking finalization
│       ├── prompt.py          # System prompt engineering & persona
│       ├── vector_store.py    # FAISS index management
│       └── retriever.py       # Similarity search logic
├── data/                      # SQLite DB and FAISS index files
├── bookings_json/             # Auto-generated booking confirmation files
├── .env                       # API Configuration
└── requirements.txt           # Project dependencies


## 📊 Database Schema
The system utilizes a relational model to maintain data integrity:

* **User**: Stores guest contact details (Name, Email, Phone).
* **Services**: Catalog of available room types and their nightly rates.
* **Bookings**: Maps users to services with specific check-in and check-out timestamps.
