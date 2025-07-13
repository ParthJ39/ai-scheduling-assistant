from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz
import re
from pydantic import Field
from pydantic_ai import Tool
from config import get_timezone_for_email, get_user_preferences
from models import CalendarEvent, TimeSlot, UserPreferences

@Tool
def get_current_date() -> str:
    """Return the current date and time with day of week for date calculations."""
    now = datetime.now()
    return f"{now.strftime('%A, %Y-%m-%d %H:%M:%S')} (Today is {now.strftime('%A')})"

@Tool  
def calculate_next_date(day_name: str, reference_date: str = None) -> str:
    """Calculate the next occurrence of a specific day (e.g., 'next Thursday', 'Monday').
    
    Args:
        day_name: Name of the day (e.g., 'thursday', 'next friday')
        reference_date: Reference date in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Date in YYYY-MM-DD format
    """
    if reference_date:
        base_date = datetime.strptime(reference_date, '%Y-%m-%d')
    else:
        base_date = datetime.now()
    
    day_name_lower = day_name.lower().strip()
    
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    # Handle "next [day]" explicitly
    if day_name_lower.startswith('next '):
        target_day_name = day_name_lower[5:]  # Remove "next "
        if target_day_name in weekdays:
            target_weekday = weekdays.index(target_day_name)
            # For "next [day]", always go to next week's occurrence
            days_ahead = (target_weekday - base_date.weekday() + 7) % 7
            if days_ahead == 0:  # If today is the target day, go to next week
                days_ahead = 7
            target_date = base_date + timedelta(days=days_ahead)
            return target_date.strftime('%Y-%m-%d')
    
    # Handle standalone day names
    if day_name_lower in weekdays:
        target_weekday = weekdays.index(day_name_lower)
        days_ahead = (target_weekday - base_date.weekday()) % 7
        if days_ahead == 0:  # If today is the target day, assume next week
            days_ahead = 7
        target_date = base_date + timedelta(days=days_ahead)
        return target_date.strftime('%Y-%m-%d')
    
    # Handle relative terms
    if 'tomorrow' in day_name_lower:
        return (base_date + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'today' in day_name_lower:
        return base_date.strftime('%Y-%m-%d')
    elif 'next week' in day_name_lower:
        return (base_date + timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Default to next business day
    days_ahead = 1
    while (base_date + timedelta(days=days_ahead)).weekday() >= 5:  # Skip weekends
        days_ahead += 1
    return (base_date + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

@Tool
def extract_duration_from_text(text: str) -> int:
    """Extract meeting duration from text (e.g., '30 minutes', '1 hour').
    
    Args:
        text: Text containing duration information
        
    Returns:
        Duration in minutes
    """
    text_lower = text.lower()
    
    patterns = [
        r'(\d+)\s*minutes?',
        r'(\d+)\s*mins?', 
        r'(\d+)\s*hours?',
        r'(\d+)\s*hrs?',
        r'for\s+(\d+)\s*minutes?',
        r'for\s+(\d+)\s*hours?',
        r'(\d+)-minute',
        r'(\d+)-hour'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            duration = int(match.group(1))
            if 'hour' in pattern or 'hr' in pattern:
                duration *= 60
            return duration
    
    return 30  # Default duration

@Tool
def get_user_timezone(email: str) -> str:
    """Get timezone for a user based on their email domain.
    
    Args:
        email: User email address
        
    Returns:
        Timezone string (e.g., 'America/New_York')
    """
    return get_timezone_for_email(email)

@Tool
def convert_time_across_timezones(iso_time: str, target_timezones: List[str]) -> Dict[str, str]:
    """Convert a time to multiple timezones for display.
    
    Args:
        iso_time: Time in ISO format
        target_timezones: List of timezone strings
        
    Returns:
        Dictionary mapping timezone to local time string
    """
    try:
        dt = datetime.fromisoformat(iso_time)
        if dt.tzinfo is None:
            dt = pytz.timezone('Asia/Kolkata').localize(dt)
        
        result = {}
        for tz_str in target_timezones:
            tz = pytz.timezone(tz_str)
            local_time = dt.astimezone(tz)
            result[tz_str] = local_time.strftime('%I:%M %p %Z')
        
        return result
    except Exception as e:
        return {tz: f"Error: {str(e)}" for tz in target_timezones}

@Tool
def check_business_hours(iso_time: str, timezone: str) -> bool:
    """Check if a time falls within business hours for a timezone.
    
    Args:
        iso_time: Time in ISO format
        timezone: Timezone string
        
    Returns:
        True if within business hours (9 AM - 6 PM, Monday-Friday)
    """
    try:
        dt = datetime.fromisoformat(iso_time)
        if dt.tzinfo is None:
            dt = pytz.timezone('Asia/Kolkata').localize(dt)
        
        tz = pytz.timezone(timezone)
        local_time = dt.astimezone(tz)
        
        # Check if weekday (Monday=0, Sunday=6)
        if local_time.weekday() >= 5:
            return False
        
        # Check if within business hours
        hour = local_time.hour
        return 9 <= hour < 18
    except:
        return False

@Tool
def find_calendar_conflicts(events: List[Dict[str, Any]], start_time: str, end_time: str, buffer_minutes: int = 15) -> List[Dict[str, Any]]:
    """Find calendar conflicts for a proposed time slot.
    
    Args:
        events: List of calendar events
        start_time: Proposed start time in ISO format
        end_time: Proposed end time in ISO format
        buffer_minutes: Buffer time to add around meetings
        
    Returns:
        List of conflicting events
    """
    try:
        proposed_start = datetime.fromisoformat(start_time)
        proposed_end = datetime.fromisoformat(end_time)
        
        # Add buffer time
        buffered_start = proposed_start - timedelta(minutes=buffer_minutes)
        buffered_end = proposed_end + timedelta(minutes=buffer_minutes)
        
        conflicts = []
        for event in events:
            event_start = datetime.fromisoformat(event['StartTime'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['EndTime'].replace('Z', '+00:00'))
            
            # Check for overlap
            if not (buffered_end <= event_start or buffered_start >= event_end):
                conflicts.append({
                    'event': event,
                    'overlap_type': 'calendar_conflict',
                    'buffer_minutes': buffer_minutes
                })
        
        return conflicts
    except Exception as e:
        return [{'error': str(e)}]

@Tool
def calculate_preference_score(start_time: str, user_preferences: Dict[str, Any]) -> float:
    """Calculate preference score for a time slot based on user preferences.
    
    Args:
        start_time: Start time in ISO format
        user_preferences: User preference dictionary
        
    Returns:
        Preference score between 0.0 and 1.0
    """
    try:
        dt = datetime.fromisoformat(start_time)
        hour = dt.hour
        
        score = 0.5  # Base score
        
        # Preferred times
        preferred_times = user_preferences.get('preferred_times', [])
        if 'morning' in preferred_times and 9 <= hour < 12:
            score += 0.3
        elif 'afternoon' in preferred_times and 13 <= hour < 17:
            score += 0.3
        elif 'evening' in preferred_times and 17 <= hour < 20:
            score += 0.2
        
        # Avoid lunch time
        if user_preferences.get('avoid_lunch', False) and 12 <= hour < 14:
            score -= 0.4
        
        # Seniority weight
        seniority = user_preferences.get('seniority_weight', 0.5)
        score = score * (0.7 + 0.6 * seniority)
        
        return max(0.0, min(1.0, score))
    except:
        return 0.5

@Tool
def generate_time_slots(date: str, duration_minutes: int, timezone: str = 'Asia/Kolkata') -> List[Dict[str, Any]]:
    """Generate available time slots for a given date.
    
    Args:
        date: Date in YYYY-MM-DD format
        duration_minutes: Meeting duration in minutes
        timezone: Timezone for slot generation
        
    Returns:
        List of time slot dictionaries
    """
    try:
        tz = pytz.timezone(timezone)
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        
        # Business hours: 9 AM to 6 PM
        start_time = tz.localize(date_obj.replace(hour=9, minute=0))
        end_time = tz.localize(date_obj.replace(hour=18, minute=0))
        
        slots = []
        current_time = start_time
        
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            slots.append({
                'start_time': current_time.isoformat(),
                'end_time': slot_end.isoformat(),
                'duration_minutes': duration_minutes,
                'time_display': current_time.strftime('%H:%M %Z')
            })
            
            current_time += timedelta(minutes=15)  # 15-minute increments
        
        return slots
    except Exception as e:
        return [{'error': str(e)}]