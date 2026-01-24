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
    retrieved = retrieve_chunks(user_input, index, lambda x: embed_texts([x]), top_k=3) if index else []
    context = "\n\n".join(r["text"] for r in retrieved)
    
    history_pairs = [(h["user"], h["assistant"]) for h in conversation_history]
    prompt_content = build_prompt(context, user_input, history_pairs)
    
    messages = [
        {"role": "system", "content": "You are Alex, the Grand Betopia Concierge."},
        {"role": "user", "content": prompt_content}
    ]
    
    # 2. First Call to check for Tool use
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
                # NEW: Fetch all 9 rooms from DB
                if call_name == "get_all_room_types":
                    from database.db_manager import db_get_all_rooms
                    result = db_get_all_rooms()

                elif call_name == "check_room_availability":
                    # Check if dates were actually provided by the AI/Guest
                    check_in = args.get('check_in')
                    check_out = args.get('check_out')
                    
                    # Logic Gate: If dates are missing, don't query occupancy
                    if not check_in or not check_out:
                        result = "INFO: I cannot check availability without specific dates. Please ask the guest for their check-in date and duration first."
                    else:
                        res = db_get_room(args['room_type'], check_in, check_out)
                        if res:
                            # Handle the 3rd 'status' element from our updated db_manager
                            status = res[2] if len(res) > 2 else "AVAILABLE"
                            result = f"Available: {args['room_type']} at ৳{res[1]:,.0f} per night."
                        else:
                            result = f"Unavailable: The {args['room_type']} is occupied for those dates."

                elif call_name == "finalize_hotel_booking":
                    result = db_execute_booking(**args)
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
            
            # Get the generator/stream from AI
            reply_stream = get_ai_response(u_input)
            
            print("\nAlex: ", end="", flush=True)
            full_reply = ""
            
            # ITERATE THROUGH STREAM (This is where speed happens)
            for chunk in reply_stream:
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
                    full_reply += content
            
            print() # New line after response is finished
            
            conversation_history.append({"user": u_input, "assistant": full_reply})
            if len(conversation_history) > 10:
                conversation_history.pop(0)

    except KeyboardInterrupt:
        print("\n👋 Goodbye.")

if __name__ == "__main__":
    main()