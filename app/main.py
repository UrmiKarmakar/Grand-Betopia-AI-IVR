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

# --- NEW MODULAR IMPORTS ---
from database.db_manager import init_db, DB_PATH
from rag.vector_store import load_faiss_index
from rag.retriever import retrieve_chunks
from rag.embeddings import embed_texts
from rag.prompt import build_prompt

# Import Skill Sets
from tools.booking_tools import BOOKING_TOOLS_LIST, BOOKING_FUNCTIONS
from tools.hotline_tools import HOTLINE_TOOLS_LIST, HOTLINE_FUNCTIONS

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INDEX_PATH = DATA_DIR / "hotel_knowledge.bin"
META_PATH = DATA_DIR / "hotel_metadata.json"

# --- AGGREGATE SKILLS ---
# The AI sees this list
ALL_TOOLS = BOOKING_TOOLS_LIST + HOTLINE_TOOLS_LIST
# The Code executes these functions
AVAILABLE_FUNCTIONS = {**BOOKING_FUNCTIONS, **HOTLINE_FUNCTIONS}

index = None
conversation_history = [] 

def get_ai_response(user_input):
    global conversation_history, index
    
    # 1. RAG Retrieval
    retrieved = retrieve_chunks(user_input, index, lambda x: embed_texts([x]), top_k=3) if index else []
    context = "\n\n".join(r["text"] for r in retrieved)
    
    history_pairs = [(h["user"], h["assistant"]) for h in conversation_history]
    prompt_content = build_prompt(context, user_input, history_pairs)
    
    # Inside get_ai_response function:
    messages = [
        {
            "role": "system", 
            "content": (
                "You are Alex, the Grand Betopia Hotel virtual concierge.\n\n"
                "STRICT WORKFLOW FOR BOOKINGS:\n"
                "1. Suggest rooms based on intent (business/leisure) and guest count. Use 'get_all_room_types'.\n"
                "2. Once a room is chosen, YOU MUST ask for: Name, Email, Phone, and Dates.\n"
                "3. CHECK AVAILABILITY using 'check_room_availability' BEFORE confirming.\n"
                "4. CALL 'finalize_hotel_booking' only after the guest says 'Yes' or 'OK' to the final summary.\n\n"
                "STRICT WORKFLOW FOR HOTLINE (Laundry/Food/Medical/Bellhop):\n"
                "1. You MUST ask for Room Number and Email first.\n"
                "2. You MUST collect category-specific details (e.g., for Laundry: wash type and cloth type).\n"
                "3. CALL 'log_service_request' to save to the database.\n\n"
                "NEVER tell a guest a task is 'done' or 'confirmed' unless the tool returns a 'SUCCESS' message."
            )
        },
        {"role": "user", "content": prompt_content}
    ]
    
    # 2. Call OpenAI with ALL tools
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages, 
        tools=ALL_TOOLS, 
        tool_choice="auto"
    )
    
    msg = response.choices[0].message
    
    # 3. Dynamic Tool Execution (The Hub)
    if msg.tool_calls:
        messages.append(msg) # Add the AI's "thought" to history
        
        for tool_call in msg.tool_calls:
            call_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            # Dynamic Execution
            if call_name in AVAILABLE_FUNCTIONS:
                try:
                    # Call the function from our dictionary
                    function_to_call = AVAILABLE_FUNCTIONS[call_name]
                    result = function_to_call(**args)
                except Exception as e:
                    result = f"System Error: {str(e)}"
            else:
                result = "Error: Tool not found."

            messages.append({
                "tool_call_id": tool_call.id, 
                "role": "tool", 
                "name": call_name, 
                "content": str(result)
            })
        
        # Get final answer after tool usage
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
    print("           GRAND BETOPIA HOTEL SYSTEM           ")
    print("      (Bookings & Guest Services Module Online)      ")
    print("-"*60)

    try:
        while True:
            # --- SINGLE ENTRANCE POINT ---
            u_input = input("\nGuest: ").strip()
            if not u_input: continue
            if u_input.lower() in ["exit", "quit", "bye"]:
                print("\nAlex: It was a pleasure serving you. Have a wonderful day!")
                break
            
            reply_stream = get_ai_response(u_input)
            
            # --- SINGLE OUTPUT POINT ---
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
        print("\n Goodbye.")

if __name__ == "__main__":
    main()