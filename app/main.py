import os
from dotenv import load_dotenv
from openai import OpenAI

from rag.pdf_loader import load_pdf
from rag.chunker import chunk_text
from rag.embeddings import embed_texts
from rag.vector_store import create_faiss_index
from rag.retriever import retrieve_chunks
from rag.prompt import build_prompt

# Environment & OpenAI client
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PDF_PATH = "data/betopia.pdf"
MAX_MEMORY_TURNS = 5

# Build RAG pipeline (one-time setup)
print(" Loading PDF...")
text = load_pdf(PDF_PATH)

print(" Chunking text...")
chunks = chunk_text(text)

print(" Creating embeddings...")
vectors = embed_texts(chunks)

print(" Building FAISS index...")
index = create_faiss_index(vectors)

# Conversation memory
conversation_history = []

def embed_query(query: str):
    """Embed a user query for retrieval."""
    return embed_texts([query])

# Chat loop
print("\n🤖 Betopia PDF Chatbot is ready! Type 'exit' to quit.\n")

try:
    while True:
        question = input("You: ").strip()

        # Exit condition
        if question.lower() == "exit":
            print("\n👋 Goodbye! Thanks for chatting with Betopia.")
            break

        # Empty input guard
        if not question:
            print("Bot: Please type something 🙂")
            continue
    
        # Retrieve relevant PDF chunks
        retrieved_chunks = retrieve_chunks(
            query=question,
            chunks=chunks,
            index=index,
            embed_func=embed_query
        )
        context = "\n\n".join(retrieved_chunks)

        # Prepare memory (last N turns)
        history_tuples = [
            (turn["user"], turn["assistant"])
            for turn in conversation_history
        ]

        # Build prompt
        prompt = build_prompt(
            context=context,
            question=question,
            history=history_tuples
        )

        # Call LLM
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        answer = response.choices[0].message.content.strip()

        print("\nBot:", answer)
        print("-" * 50)

        # Save memory
        conversation_history.append({
            "user": question,
            "assistant": answer
        })

        # Keep only last MAX_MEMORY_TURNS
        if len(conversation_history) > MAX_MEMORY_TURNS:
            conversation_history.pop(0)

except KeyboardInterrupt:
    print("\n\n👋 Chat interrupted. Goodbye!")
