# app/database/db_manager.py
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from dateutil import parser

# --- PATH LOGIC ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "hotel_ivr.db"
JSON_DIR = BASE_DIR / "bookings_json"
JSON_DIR.mkdir(exist_ok=True)

# --- HELPERS ---
def parse_to_iso(date_str):
    if not date_str: return None
    try:
        return parser.parse(date_str, default=datetime(2026, 1, 1)).strftime("%Y-%m-%d")
    except:
        return None

def save_booking_to_json(b_id, data):
    """Generates a detailed bill_json for each individual user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.Category, s.Created_At, sm.item_name, sm.price 
        FROM Services s
        JOIN Service_Menu sm ON s.Category = sm.category
        WHERE s.Room_Number = ?
    ''', (data.get('room_number'),))
    
    services = cursor.fetchall()
    service_list = [{"item": s[2], "cost": s[3], "date": s[1]} for s in services]
    service_total = sum(s[3] for s in services)
    
    bill_data = {
        "invoice_details": {
            "booking_id": b_id,
            "guest_name": data.get('guest_name', "Guest"),
            "room_number": data.get('room_number')
        },
        "booking_bill": {
            "room_type": data.get('room_type', "Standard"),
            "stay_period": f"{data.get('check_in')} to {data.get('check_out')}",
            "base_cost": data.get('booking_cost', 0.0)
        },
        "services_bill": {
            "items": service_list,
            "subtotal": service_total
        },
        "total_grand_bill": data.get('booking_cost', 0.0) + service_total
    }

    file_path = JSON_DIR / f"bill_booking_{b_id}.json"
    with open(file_path, "w") as f:
        json.dump(bill_data, f, indent=4)
    conn.close()

# --- DATABASE INIT ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS User (
            U_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT, email TEXT UNIQUE, phone TEXT,
            total_spent REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS Room_Types (
            Type_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT UNIQUE, price REAL
        );
        CREATE TABLE IF NOT EXISTS Rooms (
            Room_Number INTEGER PRIMARY KEY,
            Type_ID INTEGER,
            Status TEXT DEFAULT 'Vacant',
            FOREIGN KEY(Type_ID) REFERENCES Room_Types(Type_ID)
        );
        CREATE TABLE IF NOT EXISTS Bookings (
            B_ID INTEGER PRIMARY KEY AUTOINCREMENT, 
            U_ID INTEGER, Type_ID INTEGER, Room_Number INTEGER,
            check_in TEXT, check_out TEXT,
            booking_cost REAL DEFAULT 0.0,
            service_costs REAL DEFAULT 0.0,
            total_bill REAL DEFAULT 0.0,
            FOREIGN KEY(U_ID) REFERENCES User(U_ID),
            FOREIGN KEY(Type_ID) REFERENCES Room_Types(Type_ID),
            FOREIGN KEY(Room_Number) REFERENCES Rooms(Room_Number)
        );
        CREATE TABLE IF NOT EXISTS Services (
            S_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Room_Number INTEGER, Category TEXT, Status TEXT DEFAULT 'Pending',
            Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(Room_Number) REFERENCES Rooms(Room_Number)
        );
        CREATE TABLE IF NOT EXISTS Service_Menu (
            Menu_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, meal_type TEXT, item_name TEXT, price REAL
        );
        CREATE TABLE IF NOT EXISTS Laundry (
            L_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            S_ID INTEGER, Wash_Type TEXT, Cloth_Type TEXT, Return_By TEXT,
            FOREIGN KEY(S_ID) REFERENCES Services(S_ID) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS Food (
            F_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            S_ID INTEGER, Meal_Type TEXT, Items TEXT, Special_Notes TEXT,
            FOREIGN KEY(S_ID) REFERENCES Services(S_ID) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS Medical (
            M_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            S_ID INTEGER, Emergency_Level TEXT, Symptom_Description TEXT,
            FOREIGN KEY(S_ID) REFERENCES Services(S_ID) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS Bellhop (
            BH_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            S_ID INTEGER, Luggage_Count INTEGER, Action_Type TEXT, Destination TEXT,
            FOREIGN KEY(S_ID) REFERENCES Services(S_ID) ON DELETE CASCADE
        );
    ''')

    # 2. Populate Room Types
    cursor.execute("SELECT count(*) FROM Room_Types")
    if cursor.fetchone()[0] == 0:
        room_types = [

            ('Deluxe King', 16230.0), ('Deluxe Twin', 16230.0),
            ('Premier King', 24645.0), ('Premier Twin', 24645.0),
            ('Pacific Club Twin', 36066.0), ('Junior Suite', 48088.0),
            ('Executive Suite', 54100.0), ('Bengali Suite', 60110.0),
            ('International Suite', 72132.0)
        ]

        cursor.executemany("INSERT INTO Room_Types (name, price) VALUES (?,?)", room_types)
        conn.commit()

    # 3. Populate Physical Rooms (Safe ID version)
    cursor.execute("SELECT count(*) FROM Rooms")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT Type_ID FROM Room_Types")
        all_type_ids = [row[0] for row in cursor.fetchall()]

        physical_rooms = []
        for t_id in all_type_ids:
            for i in range(1, 6):
                room_num = (t_id * 100) + i
                physical_rooms.append((room_num, t_id))
        cursor.executemany("INSERT INTO Rooms (Room_Number, Type_ID) VALUES (?,?)", physical_rooms)

# 4. Populate Service Menu
    cursor.execute("SELECT count(*) FROM Service_Menu")
    if cursor.fetchone()[0] == 0:
        menu_items = [
            # FOOD & BEVERAGE
            ('Food', 'Breakfast', 'Breakfast Buffet', 4000.0),
            ('Food', 'Breakfast', 'Continental Platter', 1200.0),
            ('Food', 'Breakfast', 'Pancakes with Syrup', 950.0),
            ('Food', 'Breakfast', 'Omelette & Toast', 800.0),
            ('Food', 'Lunch', 'Lunch Buffet', 5500.0),
            ('Food', 'Lunch', 'Burger & Fries', 1100.0),
            ('Food', 'Lunch', 'Chicken Caesar Salad', 850.0),
            ('Food', 'Lunch', 'Pasta Alfredo', 1400.0),
            ('Food', 'Snacks', 'Club Sandwich', 750.0),
            ('Food', 'Snacks', 'French Fries', 600.0),
            ('Food', 'Snacks', 'Mineral Water (1L)', 150.0),
            ('Food', 'Dinner', 'Dinner Buffet', 9000.0),
            ('Food', 'Dinner', 'Grilled Salmon', 2200.0),
            ('Food', 'Dinner', 'Ribeye Steak', 3500.0),
            ('Food', 'Dinner', 'Seafood Platter', 15000.0),
            ('Food', 'Cafe', 'Coffee / Tea', 600.0),
            ('Food', 'Cafe', 'Pastry Slice', 900.0),
            ('Food', 'Cafe', 'Whole Cake', 6000.0),
            ('Food', 'Bar', 'Signature Cocktail', 2500.0),
            ('Food', 'Bar', 'Premium Spirit', 4000.0),
            ('Food', 'Bar', 'Bar Snacks', 1800.0),
            ('Food', 'Room Service', 'In-Room Meal Delivery', 0.0),
            ('Food', 'Room Service', 'Room Service Charge', 500.0),
            ('Food', 'Room Service', 'Late Night Service Fee', 500.0),
            ('Food', 'Events', 'Themed Buffet Night', 8000.0),
            ('Food', 'Events', 'Guest Chef Event', 12000.0),

            # LAUNDRY & HOUSEKEEPING
            ('Laundry', 'General', 'Wash & Fold (Per Load)', 800.0),
            ('Laundry', 'General', 'Wash & Iron (Per Load)', 1200.0),
            ('Laundry', 'General', 'Ironing Only (Per Item)', 300.0),
            ('Laundry', 'General', 'Dry Clean Suit', 1500.0),
            ('Laundry', 'General', 'Stain Removal', 600.0),
            ('Laundry', 'Express', 'Express Laundry Surcharge', 300.0),
            ('Housekeeping', 'General', 'Daily Room Cleaning', 0.0),
            ('Housekeeping', 'General', 'Linen & Towel Change', 0.0),
            ('Housekeeping', 'General', 'Toiletries Refill', 0.0),
            ('Housekeeping', 'General', 'Evening Turndown Service', 0.0),
            ('Housekeeping', 'Special', 'Deep Cleaning', 2500.0),
            ('Housekeeping', 'Special', 'Room Sanitization', 1500.0),
            ('Housekeeping', 'Special', 'Extra Cleaning Visit', 1200.0),
            ('Housekeeping', 'Special', 'Pet Cleaning Fee', 3500.0),

            # MEDICAL
            ('Medical', 'Emergency', 'Emergency Response', 0.0),
            ('Medical', 'Emergency', 'CPR / BLS Support', 0.0),
            ('Medical', 'Emergency', 'Basic First Aid', 0.0),
            ('Medical', 'General', 'Doctor on Call', 5000.0),
            ('Medical', 'General', 'Medication Supply', 1000.0),
            ('Medical', 'General', 'Vital Monitoring', 2500.0),
            ('Medical', 'Transport', 'Ambulance Service', 6000.0),
            ('Medical', 'Transport', 'Medical Escort', 3000.0),

            # BELLHOP
            ('Bellhop', 'General', 'Luggage Pickup', 0.0),
            ('Bellhop', 'General', 'Luggage Drop-off', 0.0),
            ('Bellhop', 'General', 'Valet Retrieval', 0.0),
            ('Bellhop', 'General', 'Airport Luggage Assistance', 1500.0),

            # FACILITIES
            ('Facilities', 'Fitness', 'Gym Access', 0.0),
            ('Facilities', 'Fitness', 'Group Fitness Class', 1200.0),
            ('Facilities', 'Fitness', 'Personal Trainer', 3500.0),
            ('Facilities', 'Pool', 'Swimming Pool Access', 0.0),
            ('Facilities', 'Pool', 'Pool Cabana', 4000.0),
            ('Facilities', 'Pool', 'Extra Pool Towel', 200.0),
            ('Facilities', 'Spa', 'Massage Therapy', 8000.0),
            ('Facilities', 'Spa', 'Facial Treatment', 5000.0),
            ('Facilities', 'Spa', 'Sauna / Steam', 2500.0),
            ('Facilities', 'Spa', 'Spa Package', 15000.0),
            ('Facilities', 'Business', 'Meeting Room', 10000.0),
            ('Facilities', 'Business', 'Conference Hall', 100000.0),
            ('Facilities', 'Business', 'AV Equipment Setup', 6000.0),
            ('Facilities', 'Family', 'Kids Club Access', 0.0),
            ('Facilities', 'Family', 'Babysitting Service', 2500.0),
            ('Facilities', 'Transport', 'Shuttle Service', 2000.0)
        ]

        cursor.executemany(
            "INSERT INTO Service_Menu (category, meal_type, item_name, price) VALUES (?,?,?,?)", 
            menu_items
        )
    conn.commit()
    conn.close()

# --- GETTERS ---
def db_get_all_rooms():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM Room_Types")
    rooms = cursor.fetchall()
    conn.close()
    return "\n".join([f"- {r[0]}: ৳{r[1]:,.0f}/night" for r in rooms])

def db_get_room(room_name, check_in, check_out):
    iso_in, iso_out = parse_to_iso(check_in), parse_to_iso(check_out)
    if not iso_in or not iso_out: return None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT rt.Type_ID, rt.price, rt.name FROM Room_Types rt
        JOIN Rooms r ON rt.Type_ID = r.Type_ID
        WHERE rt.name LIKE ? AND r.Room_Number NOT IN (
            SELECT Room_Number FROM Bookings 
            WHERE (check_in < ? AND check_out > ?)
        ) LIMIT 1
    ''', (f"%{room_name}%", iso_out, iso_in))
    res = cursor.fetchone()
    conn.close()
    return res

def db_get_available_room_number(type_id, iso_in, iso_out):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Room_Number FROM Rooms
        WHERE Type_ID = ? AND Room_Number NOT IN (
            SELECT Room_Number FROM Bookings
            WHERE (check_in < ? AND check_out > ?)
        ) LIMIT 1
    ''', (type_id, iso_out, iso_in))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def db_get_service_menu(category=None):
    """Restored: Required by hotline_tools.py to display the menu to guests."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT item_name, price FROM Service_Menu WHERE category = ?", (category,))
    else:
        cursor.execute("SELECT category, item_name, price FROM Service_Menu")
    
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        return "The menu is currently unavailable."
    
    if category:
        return "\n".join([f"- {i[0]}: ৳{i[1]:,.0f}" for i in items])
    return "\n".join([f"- [{i[0]}] {i[1]}: ৳{i[2]:,.0f}" for i in items])

# --- ACTIONS ---

def db_execute_booking(name, email, phone, room_name, check_in, check_out):
    iso_in, iso_out = parse_to_iso(check_in), parse_to_iso(check_out)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        with conn:
            cursor.execute("SELECT Type_ID, price FROM Room_Types WHERE name LIKE ? LIMIT 1", (f"%{room_name}%",))
            rt = cursor.fetchone()
            if not rt: return "ERROR: Room type not found."

            room_num = db_get_available_room_number(rt[0], iso_in, iso_out)
            if not room_num: return "ERROR: No physical rooms available."

            d1, d2 = datetime.strptime(iso_in, "%Y-%m-%d"), datetime.strptime(iso_out, "%Y-%m-%d")
            nights = max((d2 - d1).days, 1)
            booking_cost = rt[1] * nights

            cursor.execute('''
                INSERT INTO User (name, email, phone) VALUES (?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET phone=excluded.phone, name=excluded.name
            ''', (name, email, phone))
            
            cursor.execute("SELECT U_ID FROM User WHERE email=?", (email,))
            u_id = cursor.fetchone()[0]

            cursor.execute('''
                INSERT INTO Bookings (U_ID, Type_ID, Room_Number, check_in, check_out, booking_cost, total_bill) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (u_id, rt[0], room_num, iso_in, iso_out, booking_cost, booking_cost))
            b_id = cursor.lastrowid

            cursor.execute("UPDATE User SET total_spent = total_spent + ? WHERE U_ID = ?", (booking_cost, u_id))
            cursor.execute("UPDATE Rooms SET Status = 'Occupied' WHERE Room_Number = ?", (room_num,))
            
            save_booking_to_json(b_id, {
                "guest_name": name, "email": email, "room_number": room_num,
                "room_type": room_name, "check_in": iso_in, "check_out": iso_out, 
                "booking_cost": booking_cost
            })

        return f"SUCCESS: Booking #{b_id} confirmed. Total: ৳{booking_cost:,.0f}."
    except Exception as e: return f"FAILED: {str(e)}"
    finally: conn.close()

def db_modify_booking(email, current_room, **kwargs):
    """Restored: Required by booking_tools.py"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT b.B_ID, u.name, rt.name, b.Room_Number 
            FROM Bookings b 
            JOIN User u ON b.U_ID = u.U_ID
            JOIN Room_Types rt ON b.Type_ID = rt.Type_ID
            WHERE u.email = ? AND rt.name LIKE ? LIMIT 1
        ''', (email, f"%{current_room}%"))
        res = cursor.fetchone()
        if not res: return "ERROR: Booking not found."
        
        b_id = res[0]
        with conn:
            if 'new_check_in' in kwargs:
                cursor.execute("UPDATE Bookings SET check_in = ? WHERE B_ID = ?", (parse_to_iso(kwargs['new_check_in']), b_id))
            if 'new_check_out' in kwargs:
                cursor.execute("UPDATE Bookings SET check_out = ? WHERE B_ID = ?", (parse_to_iso(kwargs['new_check_out']), b_id))
        return f"SUCCESS: Booking #{b_id} modified."
    finally: conn.close()

def db_cancel_booking(email, room_name):
    """Restored: Required by booking_tools.py"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT b.B_ID FROM Bookings b 
            JOIN User u ON b.U_ID = u.U_ID
            JOIN Room_Types rt ON b.Type_ID = rt.Type_ID
            WHERE u.email = ? AND rt.name LIKE ? LIMIT 1
        ''', (email, f"%{room_name}%"))
        res = cursor.fetchone()
        if res:
            with conn: cursor.execute("DELETE FROM Bookings WHERE B_ID = ?", (res[0],))
            return f"SUCCESS: Booking #{res[0]} cancelled."
        return "ERROR: Booking not found."
    finally: conn.close()

def db_log_detailed_service(room_number, category, details):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        with conn:
            cursor.execute("INSERT INTO Services (Room_Number, Category) VALUES (?, ?)", (room_number, category))
        return f"SUCCESS: Service logged."
    except Exception as e: return f"ERROR: {str(e)}"
    finally: conn.close()

def db_order_service(email, room_number, category, item_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # 1. Fetch item details
        cursor.execute("SELECT price, meal_type FROM Service_Menu WHERE item_name = ?", (item_name,))
        res = cursor.fetchone()
        if not res:
            return f"ERROR: Item '{item_name}' not found."
        
        price, meal_type = res

        with conn:
            # 2. Log general service
            cursor.execute(
                "INSERT INTO Services (Room_Number, Category, Status) VALUES (?, ?, 'Completed')",
                (room_number, category)
            )
            s_id = cursor.lastrowid

            # 3. Log specific Food details
            if category.lower() == 'food':
                cursor.execute(
                    "INSERT INTO Food (S_ID, Meal_Type, Items) VALUES (?, ?, ?)",
                    (s_id, meal_type, item_name)
                )

            # 4. Update the Booking total bill
            cursor.execute('''
                UPDATE Bookings 
                SET service_costs = service_costs + ?, 
                    total_bill = total_bill + ?
                WHERE Room_Number = ? AND U_ID = (SELECT U_ID FROM User WHERE email = ?)
            ''', (price, price, room_number, email))

        return f"SUCCESS: {item_name} (৳{price:,.0f}) added to Room {room_number} bill."
    except Exception as e:
        return f"ERROR: {str(e)}"
    finally:
        conn.close()