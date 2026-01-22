# app/database/db_manager.py
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from dateutil import parser
from dateutil.parser import parse

# --- PATH LOGIC ---
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
        # Reference date set to Jan 21, 2026
        # Using 'parser.parse' requires 'from dateutil import parser'
        return parser.parse(date_str, default=datetime(2026, 1, 21)).strftime("%Y-%m-%d")
    except:
        return date_str

def is_valid_email(email):
    """Basic email validation to ensure data quality."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def init_db():
    """Initializes tables and seeds all room data from the guide."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS User (U_ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, phone TEXT);
        CREATE TABLE IF NOT EXISTS Services (S_ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL);
        CREATE TABLE IF NOT EXISTS Bookings (B_ID INTEGER PRIMARY KEY AUTOINCREMENT, U_ID INTEGER, S_ID INTEGER, check_in TEXT, check_out TEXT);
    ''')
    
    # Check current service count
    cursor.execute("SELECT count(*) FROM Services")
    if cursor.fetchone()[0] == 0:
        # Seed room data
        rooms = [
            ('Deluxe King', 16230.0), 
            ('Deluxe Twin', 16230.0),
            ('Premier King', 24645.0), 
            ('Premier Twin', 24645.0),
            ('Pacific Club Twin', 36066.0),
            ('Junior Suite', 48088.0),
            ('Executive Suite', 54100.0),
            ('Bengali Suite', 60110.0),
            ('International Suite', 72132.0)
        ]
        cursor.executemany("INSERT INTO Services (name, price) VALUES (?,?)", rooms)
    conn.commit()
    conn.close()

def db_get_room(room_name, check_in=None, check_out=None):
    """Fetches room price and checks availability strictly by dates, not user."""
    iso_in = parse_to_iso(check_in)
    iso_out = parse_to_iso(check_out)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Search for the room
    cursor.execute("SELECT S_ID, price FROM Services WHERE name LIKE ? LIMIT 1", (f"%{room_name}%",))
    res = cursor.fetchone()
    
    if res and iso_in and iso_out:
        # STRICT OVERLAP LOGIC: 
        # A room is taken ONLY if (Existing_In < New_Out) AND (Existing_Out > New_In)
        cursor.execute('''
            SELECT COUNT(*) FROM Bookings 
            WHERE S_ID = ? AND (check_in < ? AND check_out > ?)
        ''', (res[0], iso_out, iso_in))
        
        if cursor.fetchone()[0] > 0:
            conn.close()
            return None # Room is occupied by someone else (or a different booking by same user)
            
    conn.close()
    return res 

def db_execute_booking(name, email, phone, room_name, check_in, check_out):
    """Finalizes booking. Allows the same user (email) to have multiple bookings."""
    iso_in, iso_out = parse_to_iso(check_in), parse_to_iso(check_out)
    
    # Optional: Prevent booking if check_in and check_out are the same (0 nights)
    if iso_in == iso_out:
        return "FAILED: Check-out date must be after check-in date."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # 1. Get Room ID
        cursor.execute("SELECT S_ID, price FROM Services WHERE name LIKE ?", (f"%{room_name}%",))
        room = cursor.fetchone()
        if not room: return "ERROR: Room type not found."

        # 2. Check Overlap (Ignore User, only check the Room ID and Dates)
        cursor.execute("SELECT COUNT(*) FROM Bookings WHERE S_ID=? AND (check_in < ? AND check_out > ?)", 
                       (room[0], iso_out, iso_in))
        if cursor.fetchone()[0] > 0: 
            return "OCCUPIED: This room type is already booked for these dates."

        # 3. Handle Guest (INSERT OR IGNORE allows same user to exist, we just fetch their U_ID)
        cursor.execute("INSERT OR IGNORE INTO User (name, email, phone) VALUES (?,?,?)", (name, email, phone))
        cursor.execute("SELECT U_ID FROM User WHERE email=?", (email,))
        u_id = cursor.fetchone()[0]
        
        # 4. Save Booking (Multiple bookings for same U_ID are naturally allowed here)
        cursor.execute("INSERT INTO Bookings (U_ID, S_ID, check_in, check_out) VALUES (?,?,?,?)", 
                       (u_id, room[0], iso_in, iso_out))
        b_id = cursor.lastrowid

        # 5. Save to JSON for external verification
        booking_data = {
            "booking_id": b_id,
            "guest": {"name": name, "email": email, "phone": phone},
            "room": room_name,
            "stay": {"check_in": iso_in, "check_out": iso_out},
            "total_nights": (datetime.strptime(iso_out, "%Y-%m-%d") - datetime.strptime(iso_in, "%Y-%m-%d")).days,
            "timestamp": datetime.now().isoformat()
        }
        with open(JSON_DIR / f"booking_{b_id}.json", "w") as f:
            json.dump(booking_data, f, indent=4)

        conn.commit()
        return f"SUCCESS: Booking #{b_id} confirmed."
    except Exception as e:
        return f"FAILED: {str(e)}"
    finally:
        conn.close()

def db_cancel_booking(email, room_name):
    """Deletes booking from DB and JSON folder to free up availability."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Find the booking ID
        cursor.execute('''
            SELECT b.B_ID FROM Bookings b
            JOIN User u ON b.U_ID = u.U_ID
            JOIN Services s ON b.S_ID = s.S_ID
            WHERE u.email = ? AND s.name LIKE ?
            ORDER BY b.B_ID DESC LIMIT 1
        ''', (email, f"%{room_name}%"))
        
        res = cursor.fetchone()
        if res:
            b_id = res[0]
            cursor.execute("DELETE FROM Bookings WHERE B_ID = ?", (b_id,))
            
            # Delete JSON
            json_file = JSON_DIR / f"booking_{b_id}.json"
            if json_file.exists(): json_file.unlink()
            
            conn.commit()
            return f"SUCCESS: Booking #{b_id} cancelled. Room is now available."
        return "ERROR: No matching booking found for that email and room."
    finally:
        conn.close()

def standardize_dates(check_in_str, check_out_str=None, duration=None):
    ref_date = datetime(2026, 1, 21) 
    # This will now work without the yellow line
    start_date = parse(check_in_str, default=ref_date)

    if duration:
        # If guest said "2 nights", calculate check-out automatically
        end_date = start_date + timedelta(days=int(duration))
    else:
        # Parse the provided check-out string
        end_date = parse(check_out_str, default=ref_date)

    # Calculate actual nights for pricing
    nights = (end_date - start_date).days
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), nights

def get_total_price(rate, check_in, check_out):
    # Ensure dates are in YYYY-MM-DD format
    fmt = "%Y-%m-%d"
    d1 = datetime.strptime(check_in, fmt)
    d2 = datetime.strptime(check_out, fmt)
    nights = (d2 - d1).days
    return rate * nights