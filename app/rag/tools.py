TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_all_room_types",
            "description": "Lists all 9 room categories and their prices.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_room_availability",
            "description": "Checks if a room is available. MUST have check_in and check_out dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type": {"type": "string"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"}
                },
                "required": ["room_type", "check_in", "check_out"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finalize_hotel_booking",
            "description": "Finalizes the reservation in the database.",
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
            "name": "modify_hotel_booking",
            "description": "Updates an existing reservation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "current_room": {"type": "string"},
                    "new_room": {"type": "string"},
                    "new_check_in": {"type": "string"},
                    "new_check_out": {"type": "string"}
                },
                "required": ["email", "current_room"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_hotel_booking",
            "description": "Cancels a booking using email and room name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "room_name": {"type": "string"}
                },
                "required": ["email", "room_name"]
            }
        }
    }
]