TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_room_availability",
            "description": "Check if a specific room type is available for given dates. Use this before finalize.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type": {
                        "type": "string", 
                        "enum": ["Deluxe King", "Deluxe Twin", "Premier King", "Premier Twin", "Pacific Club Twin", "Junior Suite", "Executive Suite", "Bengali Suite", "International Suite"]
                    },
                    "check_in": {"type": "string", "description": "YYYY-MM-DD or natural date"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD or natural date"}
                },
                "required": ["room_type", "check_in", "check_out"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_all_room_types",
            "description": "Fetch all available hotel room types and their current prices from the database.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
    "type": "function",
    "function": {
        "name": "get_all_room_types",
        "description": "Fetch the full list of 9 room categories and prices from the database.",
        "parameters": {"type": "object", "properties": {}}
        }
    },
    
    {
        "type": "function",
        "function": {
            "name": "finalize_hotel_booking",
            "description": "Saves the booking to database and generates a JSON confirmation file.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_hotel_booking",
            "description": "Cancels an existing reservation. Use this when a guest wants to cancel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "The guest's email used for the booking."},
                    "room_name": {"type": "string", "description": "The name of the room type to be cancelled."}
                },
                "required": ["email", "room_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_hotel_booking",
            "description": "Changes the dates of an existing booking. Requires the Booking ID and new dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "integer", "description": "The unique B_ID from the guest's receipt."},
                    "new_check_in": {"type": "string", "description": "New check-in date (YYYY-MM-DD)."},
                    "new_check_out": {"type": "string", "description": "New check-out date (YYYY-MM-DD)."}
                },
                "required": ["booking_id", "new_check_in", "new_check_out"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_booking_by_email",
            "description": "Finds the guest's current booking ID and dates using their email address. Use this if the guest wants to modify or cancel but forgot their booking ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "The guest's email address."}
                },
                "required": ["email"]
            }
        }
    }
]