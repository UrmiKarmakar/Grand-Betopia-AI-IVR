import json
import os
from datetime import datetime

def schedule_meeting(name, email, phone):
    """
    Saves a meeting record to a local JSON database at the project root.
    """
    try:
        # Get absolute path to project root (up two levels from actions.py)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        data_dir = os.path.join(project_root, "data")
        file_path = os.path.join(data_dir, "meetings.json")

        # 1. Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)

        # 2. Prepare the new entry
        new_entry = {
            "name": name,
            "email": email,
            "phone": str(phone),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 3. Read existing data
        meetings = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    meetings = json.load(f)
                    if not isinstance(meetings, list):
                        meetings = []
                except json.JSONDecodeError:
                    meetings = []
        
        # 4. Append and Save
        meetings.append(new_entry)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(meetings, f, indent=4)

        # DEBUG message for terminal
        print(f"--> JSON Updated: {file_path}")
        
        return f"SUCCESS: Meeting saved for {name}."

    except Exception as e:
        print(f"CRITICAL ERROR SAVING JSON: {str(e)}")
        return f"ERROR: Could not save data."