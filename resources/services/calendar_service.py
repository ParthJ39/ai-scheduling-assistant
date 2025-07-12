import pytz
from logger import logger
from typing import List, Dict
from datetime import datetime, timedelta
from resources.config import calendar_config

class CalendarService:
    def __init__(self, config: Dict = None):
        self.timezone = pytz.timezone(calendar_config.default_timezone)

    def find_available_slots(self,
                             participants: List[str],
                             start_date: str,
                             end_date: str,
                             duration_minutes: int,
                             existing_events: Dict[str, List[Dict]] = None) -> List[Dict]:
        """Find available time slots for all participants"""

        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # Ensure timezone awareness
        if start_dt.tzinfo is None:
            start_dt = self.timezone.localize(start_dt)
        if end_dt.tzinfo is None:
            end_dt = self.timezone.localize(end_dt)

        available_slots = []
        current_time = start_dt

        # Generate 15-minute time slots
        while current_time + timedelta(minutes=duration_minutes) <= end_dt:
            slot_end = current_time + timedelta(minutes=duration_minutes)

            # Check if slot is within business hours
            if self._is_business_hours(current_time):

                # Check conflicts for all participants
                has_conflict = False
                if existing_events:
                    for participant in participants:
                        if self._has_participant_conflict(participant, current_time, slot_end, existing_events):
                            has_conflict = True
                            break

                if not has_conflict:
                    available_slots.append({
                        'start_time': current_time.isoformat(),
                        'end_time': slot_end.isoformat(),
                        'duration_minutes': duration_minutes,
                        'participants': participants.copy()
                    })

            current_time += timedelta(minutes=15)

        return available_slots

    def _is_business_hours(self, dt: datetime) -> bool:
        """Check if time is within business hours"""
        # Business hours: 9 AM to 6 PM, Monday to Friday
        if dt.weekday() >= 5:  # Weekend
            return False

        hour = dt.hour
        return 9 <= hour < 18

    def _has_participant_conflict(self,
                                  participant: str,
                                  start_time: datetime,
                                  end_time: datetime,
                                  existing_events: Dict[str, List[Dict]]) -> bool:
        """Check if participant has conflicts in the given time slot"""

        if participant not in existing_events:
            return False

        participant_events = existing_events[participant]

        for event in participant_events:
            event_start = datetime.fromisoformat(event['StartTime'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['EndTime'].replace('Z', '+00:00'))

            # Convert to same timezone
            if event_start.tzinfo != start_time.tzinfo:
                event_start = event_start.astimezone(start_time.tzinfo)
                event_end = event_end.astimezone(start_time.tzinfo)

            # Check for overlap
            if not (end_time <= event_start or start_time >= event_end):
                return True

        return False

    def create_calendar_event(self, event_data: Dict) -> Dict:
        """Create a calendar event (mock implementation)"""

        # In real implementation, this would create actual calendar events
        # For hackathon demo, we just return the event data

        event = {
            'id': f"event_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'subject': event_data.get('subject', 'Meeting'),
            'start_time': event_data['start_time'],
            'end_time': event_data['end_time'],
            'attendees': event_data.get('attendees', []),
            'location': event_data.get('location', ''),
            'created_at': datetime.now().isoformat(),
            'status': 'created'
        }

        logger.info(f"Mock calendar event created: {event['subject']} at {event['start_time']}")
        return event

    def send_calendar_invite(self, event_data: Dict, attendees: List[str]) -> bool:
        """Send calendar invites to attendees (mock implementation)"""

        # In real implementation, this would send actual calendar invites
        # For hackathon demo, we just simulate the sending

        logger.info(f"Mock calendar invite sent to {len(attendees)} attendees")
        logger.info(f"Event: {event_data.get('subject')} on {event_data.get('start_time')}")

        for attendee in attendees:
            logger.info(f"  - Invite sent to {attendee}")

        return True

    def update_calendar_event(self, event_id: str, updates: Dict) -> Dict:
        """Update an existing calendar event (mock implementation)"""

        logger.info(f"Mock calendar event {event_id} updated with: {updates}")

        return {
            'id': event_id,
            'status': 'updated',
            'updated_at': datetime.now().isoformat(),
            **updates
        }

    def cancel_calendar_event(self, event_id: str, reason: str = None) -> bool:
        """Cancel a calendar event (mock implementation)"""

        logger.info(f"Mock calendar event {event_id} cancelled")
        if reason:
            logger.info(f"Reason: {reason}")

        return True

    def get_timezone_info(self, participant_email: str) -> Dict:
        """Get timezone information for a participant"""

        # Mock timezone data - in real implementation, this would come from user profiles
        timezone_mapping = {
            'userthree.amd@gmail.com': 'Asia/Kolkata',
            'userone.amd@gmail.com': 'Asia/Kolkata',
            'usertwo.amd@gmail.com': 'Asia/Kolkata'
        }

        participant_tz = timezone_mapping.get(participant_email, 'Asia/Kolkata')
        tz = pytz.timezone(participant_tz)

        current_time = datetime.now(tz)

        return {
            'timezone': participant_tz,
            'offset': current_time.strftime('%z'),
            'dst_active': bool(current_time.dst()),
            'local_time': current_time.isoformat()
        }

    def convert_timezone(self, dt_str: str, from_tz: str, to_tz: str) -> str:
        """Convert datetime from one timezone to another"""

        from_timezone = pytz.timezone(from_tz)
        to_timezone = pytz.timezone(to_tz)

        # Parse datetime
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))

        # Localize if naive
        if dt.tzinfo is None:
            dt = from_timezone.localize(dt)

        # Convert to target timezone
        converted_dt = dt.astimezone(to_timezone)

        return converted_dt.isoformat()

    def get_business_hours(self, timezone_str: str = None) -> Dict:
        """Get business hours for a timezone"""

        tz = pytz.timezone(timezone_str or 'Asia/Kolkata')

        return {
            'timezone': str(tz),
            'start_hour': 9,
            'end_hour': 18,
            'working_days': [0, 1, 2, 3, 4],  # Monday to Friday
            'lunch_hours': [12, 13]  # 12 PM to 1 PM
        }
