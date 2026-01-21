import sqlite3
import json
from pathlib import Path
from datetime import datetime
from dateutil import parser

# --- PATH LOGIC ---
# This ensures paths are relative to the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "hotel_ivr.db"

JSON_DIR = BASE_DIR / "bookings_json"
JSON_DIR.mkdir(exist_ok=True)

def parse_to_iso(date_str):
    """Converts natural dates (e.g. '22 Jan') to ISO (2026-01-22)."""
    if not date_str: return None
    try:
        # Default to 2026 as per system context
        return parser.parse(date_str, default=datetime(2026, 1, 1)).strftime("%Y-%m-%d")
    except:
        return date_str

def init_db():
    """Initializes tables and seeds room data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS User (U_ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, phone TEXT);
        CREATE TABLE IF NOT EXISTS Services (S_ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL);
        CREATE TABLE IF NOT EXISTS Bookings (B_ID INTEGER PRIMARY KEY AUTOINCREMENT, U_ID INTEGER, S_ID INTEGER, check_in TEXT, check_out TEXT);
    ''')
    # Seed rooms if empty
    cursor.execute("SELECT count(*) FROM Services")
    if cursor.fetchone()[0] == 0:
        rooms = [
            ('Deluxe King', 16230.0), 
            ('Deluxe Twin', 16230.0),
            ('Premier King', 24645.0), 
            ('Premier Twin', 24645.0),
            ('Executive Suite', 54100.0),
            ('Junior Suite', 48088.0)
        ]
        cursor.executemany("INSERT INTO Services (name, price) VALUES (?,?)", rooms)
    conn.commit()
    conn.close()

def db_get_room(room_name, check_in=None, check_out=None):
    """
    REQUIRED BY MAIN.PY: Fetches room price and checks availability.
    """
    iso_in = parse_to_iso(check_in)
    iso_out = parse_to_iso(check_out)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Search for the room
    cursor.execute("SELECT S_ID, price FROM Services WHERE name LIKE ? LIMIT 1", (f"%{room_name}%",))
    res = cursor.fetchone()
    
    if res and iso_in and iso_out:
        # Check if the room is occupied during these dates
        cursor.execute('''
            SELECT COUNT(*) FROM Bookings 
            WHERE S_ID = ? AND (check_in < ? AND check_out > ?)
        ''', (res[0], iso_out, iso_in))
        
        if cursor.fetchone()[0] > 0:
            conn.close()
            return None # Room exists but is occupied
            
    conn.close()
    return res # Returns (S_ID, price) or None

def db_execute_booking(name, email, phone, room_name, check_in, check_out):
    """Finalizes booking in DB and saves a JSON file."""
    iso_in, iso_out = parse_to_iso(check_in), parse_to_iso(check_out)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # 1. Get Room ID
        cursor.execute("SELECT S_ID, price FROM Services WHERE name LIKE ?", (f"%{room_name}%",))
        room = cursor.fetchone()
        if not room: return "ERROR: Room not found."

        # 2. Check Overlap (Double check before insert)
        cursor.execute("SELECT COUNT(*) FROM Bookings WHERE S_ID=? AND (check_in < ? AND check_out > ?)", 
                       (room[0], iso_out, iso_in))
        if cursor.fetchone()[0] > 0: return "OCCUPIED: Room taken for these dates."

        # 3. Save Guest & Booking
        cursor.execute("INSERT OR IGNORE INTO User (name, email, phone) VALUES (?,?,?)", (name, email, phone))
        cursor.execute("SELECT U_ID FROM User WHERE email=?", (email,))
        u_id = cursor.fetchone()[0]
        
        cursor.execute("INSERT INTO Bookings (U_ID, S_ID, check_in, check_out) VALUES (?,?,?,?)", 
                       (u_id, room[0], iso_in, iso_out))
        b_id = cursor.lastrowid

        # 4. Save to JSON
        booking_data = {
            "booking_id": b_id,
            "guest": {"name": name, "email": email, "phone": phone},
            "room": room_name,
            "stay": {"check_in": iso_in, "check_out": iso_out},
            "timestamp": datetime.now().isoformat()
        }
        with open(JSON_DIR / f"booking_{b_id}.json", "w") as f:
            json.dump(booking_data, f, indent=4)

        conn.commit()
        return f"SUCCESS: Booking #{b_id} confirmed and JSON file created."
    except Exception as e:
        return f"FAILED: {str(e)}"
    finally:
        conn.close()