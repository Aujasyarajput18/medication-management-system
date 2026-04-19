"""
Aujasya — IST Timezone Utilities
All times in Aujasya are IST (Asia/Kolkata, UTC+5:30).
"""

from __future__ import annotations

from datetime import datetime, time, date
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    """Get current datetime in IST."""
    return datetime.now(tz=IST)


def today_ist() -> date:
    """Get today's date in IST."""
    return now_ist().date()


def to_ist(dt: datetime) -> datetime:
    """Convert a datetime to IST."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def parse_time(time_str: str) -> time:
    """
    Parse HH:MM string into a time object.
    
    Args:
        time_str: Time string in HH:MM format (e.g., "08:00")
    
    Returns:
        time object
    """
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {time_str}. Must be HH:MM")
    hours = int(parts[0])
    minutes = int(parts[1])
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError(f"Invalid time values: {time_str}")
    return time(hours, minutes)


def combine_date_time_ist(target_date: date, target_time: time) -> datetime:
    """Combine a date and time into a datetime in IST."""
    return datetime.combine(target_date, target_time, tzinfo=IST)
