# app/rag/actions.py
import logging
from datetime import datetime
from dateutil import parser
# Ensure this path matches your folder structure
from database.db_manager import db_execute_booking

logger = logging.getLogger(__name__)

def parse_date_safely(date_str):
    """Internal helper to ensure AI-provided dates are converted to YYYY-MM-DD."""
    try:
        # Default to 2026 as per your system instructions
        default_date = datetime(2026, 1, 1)
        return parser.parse(date_str, default=default_date).strftime("%Y-%m-%d")
    except Exception:
        return None

def finalize_hotel_booking(name, email, phone, room_name, check_in, check_out):
    """
    Finalizes a hotel reservation with strict date-range validation and auto-parsing.
    """
    try:
        # 1. Field Check
        if not all([name, email, phone, room_name, check_in, check_out]):
            return "ERROR: Missing details. I need Name, Email, Phone, Room Type, Check-in, and Check-out dates."

        # 2. Smart Date Parsing
        iso_in = parse_date_safely(check_in)
        iso_out = parse_date_safely(check_out)

        if not iso_in or not iso_out:
            return f"FAILED: I couldn't understand the dates ({check_in} to {check_out}). Please use YYYY-MM-DD or 'Jan 22'."

        # 3. Logic Validation
        d1 = datetime.strptime(iso_in, "%Y-%m-%d")
        d2 = datetime.strptime(iso_out, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if d1 < today:
            return f"FAILED: Check-in date ({iso_in}) cannot be in the past."
        
        if d2 <= d1:
            return f"FAILED: Check-out date ({iso_out}) must be after check-in ({iso_in})."

        # 4. Database Execution (Passes the cleaned ISO dates)
        result = db_execute_booking(
            name=name,
            email=email,
            phone=str(phone),
            room_name=room_name,
            check_in=iso_in,
            check_out=iso_out
        )

        # 5. Logging
        if "SUCCESS" in result:
            logger.info(f"Booking confirmed: {name} | {room_name} | {iso_in} to {iso_out}")
        else:
            logger.warning(f"Booking rejected: {result}")
            
        return result

    except Exception as e:
        logger.error(f"CRITICAL ERROR IN ACTION LAYER: {str(e)}")
        return f"ERROR: System error while processing booking: {str(e)}"