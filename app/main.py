import os
import time
import json
import shlex
from dotenv import load_dotenv
from openai import OpenAI

# Custom imports
from rag.pdf_loader import load_all_pdfs_text
from rag.image_reader import load_all_images_text
from rag.chunker import chunk_text
from rag.embeddings import embed_texts
from rag.vector_store import create_faiss_index
from rag.retriever import retrieve_chunks
from rag.prompt import build_prompt
from rag.upload_manager import save_uploaded_files, build_temp_index, clear_tmp_dir
from rag.actions import schedule_meeting 
from voice.stt import record_audio
from voice.stt_openai import speech_to_text
from voice.tts import speak_text

# ENV Setup
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found")

client = OpenAI(api_key=OPENAI_API_KEY)

# Define the Tool Schema
TOOLS = [{
    "type": "function",
    "function": {
        "name": "schedule_meeting",
        "description": "Saves a meeting request to the database after user confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full name of the user"},
                "email": {"type": "string", "description": "User email"},
                "phone": {"type": "string", "description": "User phone number"}
            },
            "required": ["name", "email", "phone"]
        }
    }
}]

# PATHS
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_DIR = os.path.join(DATA_DIR, "pdf")
IMAGE_DIR = os.path.join(DATA_DIR, "images")
TMP_UPLOAD_DIR = os.path.join(DATA_DIR, "tmp") 
MAX_MEMORY_TURNS = 10

# SESSION STATE
conversation_history = []
temp_index = None
meeting_scheduled_in_session = False

# HELPER FUNCTIONS

def embed_query(query: str):
    return embed_texts([query])

def show_history():
    """Prints the current session conversation in a formatted table."""
    if not conversation_history:
        print("\n📜 History is empty.")
        return
    print("\n" + "="*60)
    print(f"{'INDEX':<7} | {'SENDER':<10} | {'MESSAGE'}")
    print("-" * 60)
    for i, turn in enumerate(conversation_history):
        print(f"{i:<7} | {'User':<10} | {turn['user']}")
        # Truncate bot answer for readability in table
        bot_short = (turn['assistant'][:75] + '...') if len(turn['assistant']) > 75 else turn['assistant']
        print(f"{' ': <7} | {'Bot':<10} | {bot_short}")
    print("="*60 + "\n")

def save_session_to_file():
    """Saves the current conversation to a text file before exiting."""
    if not conversation_history:
        return
    filename = f"chat_history_{int(time.time())}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("BETOPIA CHAT SESSION HISTORY\n")
        f.write("="*40 + "\n")
        for turn in conversation_history:
            f.write(f"USER: {turn['user']}\n")
            f.write(f"BOT: {turn['assistant']}\n")
            f.write("-" * 30 + "\n")
    print(f"💾 History saved to {filename}")

# STARTUP LOGIC

print("\n Loading PDFs...")
pdf_docs = load_all_pdfs_text(PDF_DIR)
print(" Loading images...")
image_docs = load_all_images_text(IMAGE_DIR, client)

documents = []
timestamp = int(time.time())

for doc in pdf_docs:
    documents.append({"text": doc["text"], "metadata": {"source": doc["source"], "type": "pdf", "updated_at": timestamp}})
for doc in image_docs:
    documents.append({"text": doc["text"], "metadata": {"source": doc["source"], "type": "image", "updated_at": timestamp}})

if not documents:
    print(" Warning: No documents found in data/ folder")
else:
    print(f" Loaded {len(pdf_docs)} PDFs and {len(image_docs)} images")

print(" Chunking & Embedding...")
chunks, metadatas = [], []
for doc in documents:
    doc_chunks = chunk_text(doc["text"])
    chunks.extend(doc_chunks)
    metadatas.extend([doc["metadata"]] * len(doc_chunks))

if chunks:
    vectors = embed_texts(chunks)
    print(" Building FAISS index...")
    index = create_faiss_index(vectors=vectors, texts=chunks, metadatas=metadatas)
else:
    index = None
    print(" Skipping FAISS: No text chunks found.")

# MAIN INTERACTION LOOP
print("\n🤖 Betopia AI Agent Ready")
print("-" * 40)
print("COMMANDS:")
print("• [Type Text] + Enter : Normal Chat")
print("• [Empty Enter]      : Voice Input Mode")
print("• /history           : View session logs")
print("• /upload <path>     : Add temp files")
print("• /clear             : Delete temp uploads")
print("• exit               : Save & Close")
print("-" * 40)

try:
    while True:
        raw_input = input("You: ").strip()
        is_voice_mode = False
        user_input = raw_input

        # 1. HANDLE VOICE & EXIT
        if raw_input == "":
            is_voice_mode = True
            audio_path = record_audio()
            user_input = speech_to_text(client, audio_path)
            if not user_input or len(user_input.strip()) < 2: 
                continue
            print(f"🗣️ You said: {user_input}")

        if user_input.lower() == "exit":
            save_session_to_file()
            break

        # 2. HANDLE COMMANDS
        if user_input.lower() == "/history":
            show_history()
            continue

        if user_input.lower() == "/clear":
            clear_tmp_dir(TMP_UPLOAD_DIR)
            temp_index = None
            print(" All temporary uploads and their indices have been deleted.")
            continue

        if user_input.startswith("/upload"):
            try:
                paths = shlex.split(user_input)[1:]
                clean_paths = [p.strip('"').replace("\\", "/") for p in paths]
                save_uploaded_files(TMP_UPLOAD_DIR, clean_paths)
                temp_index = build_temp_index(TMP_UPLOAD_DIR, client)
                print(" Knowledge Base updated with uploaded files.")
            except Exception as e:
                print(f" Upload Error: {e}")
            continue

        # 3. RAG RETRIEVAL
        retrieved = []
        if index:
            retrieved = retrieve_chunks(user_input, index, embed_query, top_k=5)
        
        if temp_index:
            retrieved_tmp = retrieve_chunks(user_input, temp_index, embed_query, top_k=3)
            retrieved.extend(retrieved_tmp)
        
        context = "\n\n".join(r["text"] for r in retrieved)
        history_pairs = [(h["user"], h["assistant"]) for h in conversation_history]
        
        # 4. AGENT LLM CALL 
        # Pass meeting_scheduled_in_session to build_prompt to update the AI's behavior
        prompt = build_prompt(context, user_input, history_pairs, meeting_status=meeting_scheduled_in_session)
        messages = [{"role": "user", "content": prompt}]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # 5. HANDLE AGENT ACTIONS
        if tool_calls:
            messages.append(response_message)
            for tool_call in tool_calls:
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute tool: This now saves to meetings.json via actions.py
                action_result = schedule_meeting(
                    name=function_args.get("name"),
                    email=function_args.get("email"),
                    phone=function_args.get("phone")
                )
                
                # If tool succeeds, lock the session so it doesn't ask again
                if "SUCCESS" in action_result:
                    meeting_scheduled_in_session = True

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "schedule_meeting",
                    "content": action_result,
                })

            second_response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            answer = second_response.choices[0].message.content
        else:
            answer = response_message.content

        # 6. OUTPUT & SAVE
        print(f"\n🤖 Bot: {answer}")
        if is_voice_mode: 
            speak_text(client, answer)
        
        print("-" * 60)
        conversation_history.append({"user": user_input, "assistant": answer})
        if len(conversation_history) > MAX_MEMORY_TURNS:
            conversation_history.pop(0)

except KeyboardInterrupt:
    print("\n👋 System Offline.")
finally:
    clear_tmp_dir(TMP_UPLOAD_DIR)
