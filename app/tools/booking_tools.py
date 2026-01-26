# app/tools/booking_tools.py
from database.db_manager import (
    db_get_all_rooms, 
    db_get_room, 
    db_execute_booking, 
    db_modify_booking, 
    db_cancel_booking,
    db_get_available_room_number
)

# 1. The Logic Wrapper
def check_availability_wrapper(room_type, check_in, check_out):
    """Bridge between AI and DB to check physical room inventory."""
    try:
        res = db_get_room(room_type, check_in, check_out)
        if res:
            # res[0]: Type_ID, res[1]: Price, res[2]: Full Room Name
            room_num = db_get_available_room_number(res[0], check_in, check_out)
            if room_num:
                return f"SUCCESS: {res[2]} is available (Room {room_num}) at ৳{res[1]:,.0f}/night."
            return f"FULL: The {res[2]} is fully booked for these dates. Please suggest a different room category."
        return "NOT_FOUND: I couldn't find that room type. Use 'get_all_room_types' to see valid options."
    except Exception as e:
        return f"ERROR: Database communication failed: {str(e)}"

# 2. The Tool Definitions
BOOKING_TOOLS_LIST = [
    {
        "type": "function",
        "function": {
            "name": "get_all_room_types",
            "description": "Returns a list of all 9 room categories and prices. Use this if a specific room is full.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_room_availability",
            "description": "Checks if a room type has any vacant units for specific dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type": {"type": "string"},
                    "check_in": {"type": "string", "description": "YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["room_type", "check_in", "check_out"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finalize_hotel_booking",
            "description": "Saves the booking. Call ONLY when you have Name, Email, and Phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "room_name": {"type": "string"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"}
                },
                "required": ["name", "email", "phone", "room_name", "check_in", "check_out"]
            }
        }
    }
]

# 3. The Mapping
BOOKING_FUNCTIONS = {
    "get_all_room_types": db_get_all_rooms,
    "check_room_availability": check_availability_wrapper,
    "finalize_hotel_booking": db_execute_booking
}