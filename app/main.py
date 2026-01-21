# app/main.py
import os
import json
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Standard Path setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Silence excessive logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Database and RAG Imports
from database.db_manager import init_db, db_get_room, db_execute_booking, db_cancel_booking
from rag.vector_store import load_faiss_index
from rag.retriever import retrieve_chunks
from rag.embeddings import embed_texts
from rag.prompt import build_prompt
from rag.tools import TOOLS

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INDEX_PATH = DATA_DIR / "hotel_knowledge.bin"
META_PATH = DATA_DIR / "hotel_metadata.json"

index = None
conversation_history = [] 

def get_ai_response(user_input):
    global conversation_history, index
    
    # 1. RAG Retrieval
    retrieved = retrieve_chunks(user_input, index, lambda x: embed_texts([x]), top_k=5) if index else []
    context = "\n\n".join(r["text"] for r in retrieved)
    
    # 2. History Formatting
    history_pairs = [(h["user"], h["assistant"]) for h in conversation_history]
    
    # 3. Build Prompt
    prompt_content = build_prompt(context, user_input, history_pairs)
    
    messages = [
        {"role": "system", "content": "You are Alex, the Grand Betopia Concierge. Always use tools to verify availability, save, or cancel bookings. Today is January 21, 2026."},
        {"role": "user", "content": prompt_content}
    ]
    
    # 4. Initial OpenAI Call
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages, 
        tools=TOOLS, 
        tool_choice="auto"
    )
    
    msg = response.choices[0].message
    
    # 5. Tool Handling Logic
    if msg.tool_calls:
        messages.append(msg)
        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments)
            call_name = tool_call.function.name
            
            try:
                if call_name == "check_room_availability":
                    res = db_get_room(args['room_type'], args['check_in'], args['check_out'])
                    result = f"Available: {args['room_type']} at ৳{res[1]} per night." if res else "Unavailable: Occupied."
                
                elif call_name == "finalize_hotel_booking":
                    result = db_execute_booking(**args)
                    
                elif call_name == "cancel_hotel_booking":
                    # Integration with the new Cancellation function
                    result = db_cancel_booking(args['email'], args['room_name'])
                else:
                    result = "Error: Tool not found."
            
            except Exception as e:
                result = f"System Error: {str(e)}"

            messages.append({
                "tool_call_id": tool_call.id, 
                "role": "tool", 
                "name": call_name, 
                "content": result
            })
        
        # Second call to generate the verbal response based on tool results
        final_res = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        return final_res.choices[0].message.content
    
    return msg.content

def main():
    global index
    init_db()  
    
    if INDEX_PATH.exists():
        index = load_faiss_index(str(INDEX_PATH), str(META_PATH))
        print(" Knowledge Base Loaded.")
    else:
        print(" Warning: Knowledge base not found.")

    print("\n" + "-"*60)
    print("           GRAND BETOPIA HOTEL IVR SYSTEM           ")
    print("-"*60)

    try:
        while True:
            u_input = input("\nGuest: ").strip()
            if not u_input: continue
            if u_input.lower() in ["exit", "quit", "bye"]:
                print("\nAlex: It was a pleasure serving you. Have a wonderful day!")
                break
            
            reply = get_ai_response(u_input)
            print(f"\nAlex: {reply}")
            
            conversation_history.append({"user": u_input, "assistant": reply})
            if len(conversation_history) > 10:
                conversation_history.pop(0)

    except KeyboardInterrupt:
        print("\n👋 Goodbye.")

if __name__ == "__main__":
    main()