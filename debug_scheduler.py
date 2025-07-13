#!/usr/bin/env python3
"""
Debug script to find why no slots are available
"""

from datetime import datetime, timedelta
import pytz
from participant_agent import ParticipantAgent
from mock_data import USER_PREFERENCES

def debug_participant_availability():
    """Debug each participant's availability"""
    
    # Test participants
    test_participants = [
        "userone.amd@gmail.com",
        "usertwo.amd@gmail.com", 
        "userthree.amd@gmail.com"
    ]
    
    # Target date from your request
    target_date = "2025-07-17"  # Thursday
    duration_mins = 30
    
    print(f"🔍 Debugging availability for {target_date}")
    print("=" * 60)
    
    for email in test_participants:
        print(f"\n👤 Checking {email}:")
        
        # Get mock calendar data
        calendar_events = get_mock_calendar_for_user(email, target_date)
        print(f"   📅 Calendar events: {len(calendar_events)}")
        for event in calendar_events:
            print(f"      • {event['StartTime']} - {event['EndTime']}: {event['Summary']}")
        
        # Get preferences
        preferences = USER_PREFERENCES.get(email, {
            'preferred_times': ['morning', 'afternoon'],
            'buffer_minutes': 15,
            'timezone': 'Asia/Kolkata',
            'avoid_lunch': True,
            'seniority_weight': 0.5
        })
        print(f"   ⚙️  Preferences: {preferences}")
        
        # Create participant agent
        agent = ParticipantAgent(
            email=email,
            calendar_data=calendar_events,
            preferences=preferences
        )
        
        # Check availability
        available_slots = agent.find_available_slots(target_date, duration_mins)
        print(f"   ✅ Available slots: {len(available_slots)}")
        
        for i, slot in enumerate(available_slots[:5]):  # Show first 5
            start_time = datetime.fromisoformat(slot['start_time'])
            print(f"      {i+1}. {start_time.strftime('%H:%M')} - score: {slot['preference_score']:.2f}")
        
        if not available_slots:
            print("   ❌ NO AVAILABLE SLOTS - Debugging why...")
            debug_working_hours(agent, target_date)

def get_mock_calendar_for_user(email: str, target_date: str) -> list:
    """Get mock calendar events for debugging"""
    
    # Enhanced mock data for the specific date
    mock_calendars = {
        "userone.amd@gmail.com": [
            {
                "StartTime": f"{target_date}T00:00:00+05:30",
                "EndTime": f"{target_date}T09:00:00+05:30",
                "NumAttendees": 1,
                "Attendees": ["SELF"],
                "Summary": "Off Hours"
            },
            {
                "StartTime": f"{target_date}T18:00:00+05:30",
                "EndTime": f"{target_date}T23:59:59+05:30",
                "NumAttendees": 1,
                "Attendees": ["SELF"],
                "Summary": "Off Hours"
            }
        ],
        "usertwo.amd@gmail.com": [
            {
                "StartTime": f"{target_date}T00:00:00+05:30",
                "EndTime": f"{target_date}T09:00:00+05:30",
                "NumAttendees": 1,
                "Attendees": ["SELF"],
                "Summary": "Off Hours"
            },
            {
                "StartTime": f"{target_date}T10:00:00+05:30",
                "EndTime": f"{target_date}T10:30:00+05:30",
                "NumAttendees": 2,
                "Attendees": ["userone.amd@gmail.com", "usertwo.amd@gmail.com"],
                "Summary": "Team Sync"
            },
            {
                "StartTime": f"{target_date}T18:00:00+05:30",
                "EndTime": f"{target_date}T23:59:59+05:30",
                "NumAttendees": 1,
                "Attendees": ["SELF"],
                "Summary": "Off Hours"
            }
        ],
        "userthree.amd@gmail.com": [
            {
                "StartTime": f"{target_date}T00:00:00+05:30",
                "EndTime": f"{target_date}T09:00:00+05:30",
                "NumAttendees": 1,
                "Attendees": ["SELF"],
                "Summary": "Off Hours"
            },
            {
                "StartTime": f"{target_date}T13:00:00+05:30",
                "EndTime": f"{target_date}T14:00:00+05:30",
                "NumAttendees": 1,
                "Attendees": ["SELF"],
                "Summary": "Lunch with Customers"
            },
            {
                "StartTime": f"{target_date}T18:00:00+05:30",
                "EndTime": f"{target_date}T23:59:59+05:30",
                "NumAttendees": 1,
                "Attendees": ["SELF"],
                "Summary": "Off Hours"
            }
        ]
    }
    
    return mock_calendars.get(email, [])

def debug_working_hours(agent, target_date):
    """Debug working hours calculation"""
    target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    working_start, working_end = agent._get_working_hours_from_calendar(target_date_obj)
    
    print(f"      🕐 Working hours: {working_start.strftime('%H:%M')} - {working_end.strftime('%H:%M')}")
    
    # Check specific time slots manually
    timezone = pytz.timezone('Asia/Kolkata')
    test_times = [
        timezone.localize(datetime.combine(target_date_obj, datetime.min.time().replace(hour=h)))
        for h in range(9, 18)  # 9 AM to 6 PM
    ]
    
    print(f"      🔍 Checking hourly slots:")
    for test_time in test_times:
        slot_end = test_time + timedelta(minutes=30)
        has_conflict = agent._has_conflict(test_time, slot_end)
        preference_score = agent._calculate_preference_score(test_time)
        
        status = "❌ CONFLICT" if has_conflict else "✅ FREE"
        print(f"         {test_time.strftime('%H:%M')}: {status} (score: {preference_score:.2f})")

def debug_common_slots():
    """Debug why no common slots are found"""
    print(f"\n🤝 Debugging Common Slots Algorithm")
    print("=" * 60)
    
    target_date = "2025-07-17"
    duration_mins = 30
    
    # Create all agents
    agents = {}
    all_available_slots = {}
    
    for email in ["userone.amd@gmail.com", "usertwo.amd@gmail.com", "userthree.amd@gmail.com"]:
        calendar_events = get_mock_calendar_for_user(email, target_date)
        preferences = USER_PREFERENCES.get(email, {
            'preferred_times': ['morning', 'afternoon'],
            'buffer_minutes': 15,
            'timezone': 'Asia/Kolkata',
            'avoid_lunch': True,
            'seniority_weight': 0.5
        })
        
        agent = ParticipantAgent(email=email, calendar_data=calendar_events, preferences=preferences)
        agents[email] = agent
        
        slots = agent.find_available_slots(target_date, duration_mins)
        all_available_slots[email] = slots
        print(f"📋 {email}: {len(slots)} slots")
    
    # Find overlaps manually
    print(f"\n🔍 Finding Common Slots:")
    
    if not all_available_slots:
        print("❌ No participant slots found!")
        return
    
    # Get all unique time combinations
    all_time_slots = set()
    for participant_slots in all_available_slots.values():
        for slot in participant_slots:
            slot_key = (slot['start_time'], slot['end_time'])
            all_time_slots.add(slot_key)
    
    print(f"📊 Total unique time slots across all participants: {len(all_time_slots)}")
    
    # Check each time slot
    common_slots = []
    for start_time, end_time in all_time_slots:
        participants_available = []
        
        for participant_email, participant_slots in all_available_slots.items():
            has_slot = any(
                slot['start_time'] == start_time and slot['end_time'] == end_time
                for slot in participant_slots
            )
            if has_slot:
                participants_available.append(participant_email)
        
        if len(participants_available) == len(all_available_slots):
            common_slots.append((start_time, end_time))
            start_dt = datetime.fromisoformat(start_time)
            print(f"✅ Common slot: {start_dt.strftime('%H:%M')} - all participants available")
        else:
            start_dt = datetime.fromisoformat(start_time)
            print(f"❌ {start_dt.strftime('%H:%M')}: only {len(participants_available)}/{len(all_available_slots)} available")
    
    print(f"\n🎯 Final result: {len(common_slots)} common slots found")

def test_simple_availability():
    """Test with completely free calendars"""
    print(f"\n🧪 Testing with Free Calendars")
    print("=" * 60)
    
    target_date = "2025-07-17"
    
    # Create agent with no calendar conflicts
    empty_calendar = []
    simple_preferences = {
        'preferred_times': ['morning', 'afternoon'],
        'buffer_minutes': 5,  # Minimal buffer
        'timezone': 'Asia/Kolkata',
        'avoid_lunch': False,  # Don't avoid lunch
        'seniority_weight': 0.5
    }
    
    agent = ParticipantAgent(
        email="test@gmail.com",
        calendar_data=empty_calendar,
        preferences=simple_preferences
    )
    
    slots = agent.find_available_slots(target_date, 30)
    print(f"🎯 Free calendar availability: {len(slots)} slots")
    
    for i, slot in enumerate(slots[:10]):
        start_time = datetime.fromisoformat(slot['start_time'])
        print(f"   {i+1}. {start_time.strftime('%H:%M')} IST - score: {slot['preference_score']:.2f}")

if __name__ == "__main__":
    print("🚀 Debugging Scheduler Availability Issues")
    print("=" * 80)
    
    # Debug individual participants
    debug_participant_availability()
    
    # Debug common slot algorithm
    debug_common_slots()
    
    # Test with simple case
    test_simple_availability()
    
    print(f"\n💡 Recommendations:")
    print(f"   1. Check if Off Hours events are blocking too much time")
    print(f"   2. Verify working hours calculation is correct") 
    print(f"   3. Reduce buffer time requirements")
    print(f"   4. Check preference scoring isn't too restrictive")