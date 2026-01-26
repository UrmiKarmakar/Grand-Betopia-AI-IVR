# app/tools/hotline_tools.py
from database.db_manager import db_get_service_menu, db_order_service

def get_menu_wrapper(category):
    return f"Here is our {category} menu:\n" + db_get_service_menu(category)

HOTLINE_TOOLS_LIST = [
    {
        "type": "function",
        "function": {
            "name": "get_service_menu",
            "description": "Shows the guest the available items and prices for a category (Food, Laundry, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["Food", "Laundry", "Medical", "Bellhop"]}
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "order_service_item",
            "description": "Places an order for a specific item from the menu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "room_number": {"type": "integer"},
                    "category": {"type": "string"},
                    "item_name": {"type": "string"}
                },
                "required": ["email", "room_number", "category", "item_name"]
            }
        }
    }
]

HOTLINE_FUNCTIONS = {
    "get_service_menu": get_menu_wrapper,
    "order_service_item": db_order_service
}