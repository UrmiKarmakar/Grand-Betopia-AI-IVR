import sqlite3
import json
import re
import os
from pathlib import Path
from datetime import datetime, timedelta
from dateutil import parser

# --- PATH LOGIC ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "hotel_ivr.db"

JSON_DIR = BASE_DIR / "bookings_json"
JSON_DIR.mkdir(exist_ok=True)

def parse_to_iso(date_str):
    if not date_str: return None
    try:
        # Reference date set to Jan 2026
        return parser.parse(date_str, default=datetime(2026, 1, 1)).strftime("%Y-%m-%d")
    except:
        return None

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS User (
            U_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT, 
            email TEXT UNIQUE, 
            phone TEXT
        );
        CREATE TABLE IF NOT EXISTS Services (
            S_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT UNIQUE, 
            price REAL
        );
        CREATE TABLE IF NOT EXISTS Bookings (
            B_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
            U_ID INTEGER, 
            S_ID INTEGER, 
            check_in TEXT, 
            check_out TEXT,
            FOREIGN KEY(U_ID) REFERENCES User(U_ID),
            FOREIGN KEY(S_ID) REFERENCES Services(S_ID)
        );
    ''')
    
    cursor.execute("SELECT count(*) FROM Services")
    if cursor.fetchone()[0] == 0:
        rooms = [
            ('Deluxe King', 16230.0), ('Deluxe Twin', 16230.0),
            ('Premier King', 24645.0), ('Premier Twin', 24645.0),
            ('Pacific Club Twin', 36066.0), ('Junior Suite', 48088.0),
            ('Executive Suite', 54100.0), ('Bengali Suite', 60110.0),
            ('International Suite', 72132.0)
        ]
        cursor.executemany("INSERT INTO Services (name, price) VALUES (?,?)", rooms)
    conn.commit()
    conn.close()

def db_get_all_rooms():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM Services")
    rooms = cursor.fetchall()
    conn.close()
    return "\n".join([f"- {r[0]}: ৳{r[1]:,.0f}" for r in rooms])

def db_get_room(room_name, check_in, check_out):
    iso_in, iso_out = parse_to_iso(check_in), parse_to_iso(check_out)
    if not iso_in or not iso_out: return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT S_ID, price FROM Services WHERE name LIKE ? LIMIT 1", (f"%{room_name}%",))
    res = cursor.fetchone()
    
    if not res:
        conn.close()
        return None

    cursor.execute('''
        SELECT COUNT(*) FROM Bookings 
        WHERE S_ID = ? AND (check_in < ? AND check_out > ?)
    ''', (res[0], iso_out, iso_in))
    
    occupied = cursor.fetchone()[0] > 0
    conn.close()
    return None if occupied else (res[0], res[1])

def db_execute_booking(name, email, phone, room_name, check_in, check_out):
    iso_in, iso_out = parse_to_iso(check_in), parse_to_iso(check_out)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        with conn:
            cursor.execute("SELECT S_ID, price FROM Services WHERE name LIKE ? LIMIT 1", (f"%{room_name}%",))
            room = cursor.fetchone()
            if not room: return "ERROR: Room not found."

            cursor.execute('''
                INSERT INTO User (name, email, phone) VALUES (?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET phone=excluded.phone, name=excluded.name
            ''', (name, email, phone))
            
            cursor.execute("SELECT U_ID FROM User WHERE email=?", (email,))
            u_id = cursor.fetchone()[0]

            cursor.execute("INSERT INTO Bookings (U_ID, S_ID, check_in, check_out) VALUES (?, ?, ?, ?)",
                           (u_id, room[0], iso_in, iso_out))
            b_id = cursor.lastrowid

            # JSON Confirmation
            nights = max((datetime.strptime(iso_out, "%Y-%m-%d") - datetime.strptime(iso_in, "%Y-%m-%d")).days, 1)
            data = {"booking_id": b_id, "guest": email, "room": room_name, "total": room[1]*nights}
            with open(JSON_DIR / f"booking_{b_id}.json", "w") as f:
                json.dump(data, f, indent=4)

        return f"SUCCESS: Booking #{b_id} confirmed."
    except Exception as e:
        return f"FAILED: {str(e)}"
    finally:
        conn.close()

def db_modify_booking(email, current_room, new_room=None, new_check_in=None, new_check_out=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # 1. Locate the existing booking
        cursor.execute('''
            SELECT b.B_ID FROM Bookings b JOIN User u ON b.U_ID = u.U_ID
            JOIN Services s ON b.S_ID = s.S_ID
            WHERE u.email = ? AND s.name LIKE ? ORDER BY b.B_ID DESC LIMIT 1
        ''', (email, f"%{current_room}%"))
        res = cursor.fetchone()
        if not res: return "ERROR: No existing booking found for this email and room."
        
        b_id = res[0]
        
        # 2. Update Database via transaction
        with conn:
            if new_room:
                cursor.execute("SELECT S_ID FROM Services WHERE name LIKE ?", (f"%{new_room}%",))
                s_id = cursor.fetchone()
                if s_id: cursor.execute("UPDATE Bookings SET S_ID = ? WHERE B_ID = ?", (s_id[0], b_id))
            
            if new_check_in: 
                cursor.execute("UPDATE Bookings SET check_in = ? WHERE B_ID = ?", (parse_to_iso(new_check_in), b_id))
            if new_check_out: 
                cursor.execute("UPDATE Bookings SET check_out = ? WHERE B_ID = ?", (parse_to_iso(new_check_out), b_id))

        # 3. Synchronize JSON (Fetch fresh data from DB to ensure file accuracy)
        cursor.execute('''
            SELECT s.name, s.price, b.check_in, b.check_out 
            FROM Bookings b JOIN Services s ON b.S_ID = s.S_ID WHERE b.B_ID = ?
        ''', (b_id,))
        updated = cursor.fetchone()
        
        if updated:
            nights = max((datetime.strptime(updated[3], "%Y-%m-%d") - datetime.strptime(updated[2], "%Y-%m-%d")).days, 1)
            data = {
                "booking_id": b_id,
                "guest": email,
                "room": updated[0],
                "total": updated[1] * nights,
                "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(JSON_DIR / f"booking_{b_id}.json", "w") as f:
                json.dump(data, f, indent=4)
        
        return f"SUCCESS: Booking #{b_id} updated."
    except Exception as e:
        return f"ERROR: {str(e)}"
    finally:
        conn.close()

def db_cancel_booking(email, room_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT b.B_ID FROM Bookings b JOIN User u ON b.U_ID = u.U_ID
            JOIN Services s ON b.S_ID = s.S_ID
            WHERE u.email = ? AND s.name LIKE ? LIMIT 1
        ''', (email, f"%{room_name}%"))
        res = cursor.fetchone()
        if res:
            b_id = res[0]
            with conn:
                cursor.execute("DELETE FROM Bookings WHERE B_ID = ?", (b_id,))
            
            # Remove JSON file upon cancellation
            json_file = JSON_DIR / f"booking_{b_id}.json"
            if json_file.exists():
                json_file.unlink()
                
            return f"SUCCESS: Booking #{b_id} cancelled."
        return "ERROR: Booking not found."
    finally:
        conn.close()