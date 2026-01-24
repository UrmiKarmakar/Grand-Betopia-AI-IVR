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
from database.db_manager import (
    init_db, 
    db_get_room, 
    db_execute_booking, 
    db_cancel_booking, 
    db_modify_booking, 
    db_get_all_rooms
)
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
    retrieved = retrieve_chunks(user_input, index, lambda x: embed_texts([x]), top_k=3) if index else []
    context = "\n\n".join(r["text"] for r in retrieved)
    
    history_pairs = [(h["user"], h["assistant"]) for h in conversation_history]
    prompt_content = build_prompt(context, user_input, history_pairs)
    
    messages = [
        {
            "role": "system", 
            "content": (
                "You are Alex, the Grand Betopia Concierge. "
                "STRICT BOOKING RULES:\n"
                "1. If a guest selects a room, you MUST ask for BOTH check-in and check-out dates before checking availability.\n"
                "2. To modify an existing booking, you MUST extract the guest's email from the history or ask for it.\n"
                "3. Never confirm a booking or modification unless the tool returns a SUCCESS message.\n"
                "4. If a tool returns an error, explain the issue politely to the guest."
            )
        },
        {"role": "user", "content": prompt_content}
    ]
    
    # 2. Call to check for Tool use
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages, 
        tools=TOOLS, 
        tool_choice="auto"
    )
    
    msg = response.choices[0].message
    
    # 3. Tool Handling Logic
    if msg.tool_calls:
        messages.append(msg)
        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments)
            call_name = tool_call.function.name
            
            try:
                if call_name == "get_all_room_types":
                    result = db_get_all_rooms()
                elif call_name == "check_room_availability":
                    check_in, check_out = args.get('check_in'), args.get('check_out')
                    if not check_in or not check_out:
                        result = "INFO: Missing dates. Ask the guest for check-in and check-out dates."
                    else:
                        res = db_get_room(args['room_type'], check_in, check_out)
                        result = f"Available: {args['room_type']} at ৳{res[1]:,.0f}/night." if res else "Occupied."
                elif call_name == "finalize_hotel_booking":
                    result = db_execute_booking(**args)
                elif call_name == "modify_hotel_booking":
                    # The AI must extract 'current_room' from conversation history 
                    # and 'new_room' from the latest request.
                    if not args.get('email'):
                        result = "ERROR: Email required for modification. Ask the guest for the email used for the booking."
                    else:
                        result = db_modify_booking(**args)
                elif call_name == "cancel_hotel_booking":
                    result = db_cancel_booking(args['email'], args['room_name'])
                else:
                    result = "Error: Tool not found."
            except Exception as e:
                result = f"System Error: {str(e)}"

            messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": call_name, "content": result})
        
        return client.chat.completions.create(model="gpt-4o-mini", messages=messages, stream=True)
    
    return client.chat.completions.create(model="gpt-4o-mini", messages=messages, stream=True)

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
            
            reply_stream = get_ai_response(u_input)
            print("\nAlex: ", end="", flush=True)
            full_reply = ""
            
            for chunk in reply_stream:
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
                    full_reply += content
            
            print() 
            conversation_history.append({"user": u_input, "assistant": full_reply})
            if len(conversation_history) > 10:
                conversation_history.pop(0)

    except KeyboardInterrupt:
        print("\n👋 Goodbye.")

if __name__ == "__main__":
    main()