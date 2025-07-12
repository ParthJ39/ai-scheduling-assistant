import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pytz
import re
from participants_agent import ParticipantAgent
from negotiator_agent import NegotiatorAgent
from calendar_service import CalendarService
from services.llm_service import LLMService
from utils.json_validator import JSONValidator
from mock_data import USER_PREFERENCES

logging.basicConfig(level=logging.INFO)

class CoordinatorAgent:
    def __init__(self, llm_client=None):
        
        self.llm = llm_client or LLMService()
        self.negotiator = NegotiatorAgent(self.llm)
        self.calendar_service = CalendarService()
        self.validator = JSONValidator()
        self.participants = {}
        
    def _extract_duration_from_email(self, email_content: str) -> str:
        patterns = [
            r'(\d+)\s*minutes?',
            r'(\d+)\s*mins?',
            r'(\d+)\s*hours?',
            r'(\d+)\s*hrs?',
            r'for\s+(\d+)\s*minutes?',
            r'for\s+(\d+)\s*hours?'
        ]
        for pattern in patterns:
            match = re.search(pattern, email_content.lower())
            if match:
                duration = int(match.group(1))
                if 'hour' in pattern or 'hr' in pattern:
                    duration *= 60
                return str(duration)
        return "30"
    
    def _transform_input_format(self, meeting_request: Dict) -> Dict:
        email_content = meeting_request.get('EmailContent', '')
        duration_mins = self._extract_duration_from_email(email_content)
        
        from_email = meeting_request.get('From', '')
        attendee_emails = [att.get('email') for att in meeting_request.get('Attendees', [])]
        if from_email and from_email not in attendee_emails:
            attendee_emails.append(from_email)
        
        transformed_attendees = []
        for email in attendee_emails:
            mock_events = self._get_mock_events_for_user(email)
            transformed_attendees.append({
                'email': email,
                'events': mock_events
            })
        
        transformed_request = meeting_request.copy()
        transformed_request['Duration_mins'] = duration_mins
        transformed_request['Attendees'] = transformed_attendees
        return transformed_request
    
    def _get_mock_events_for_user(self, email: str) -> List[Dict]:
        mock_calendars = {
            "usertwo.amd@gmail.com": [
                {
                    "StartTime": "2025-07-17T10:00:00+05:30",
                    "EndTime": "2025-07-17T10:30:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": ["userone.amd@gmail.com", "usertwo.amd@gmail.com", "userthree.amd@gmail.com"],
                    "Summary": "Team Meet"
                }
            ],
            "userthree.amd@gmail.com": [
                {
                    "StartTime": "2025-07-17T10:00:00+05:30",
                    "EndTime": "2025-07-17T10:30:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": ["userone.amd@gmail.com", "usertwo.amd@gmail.com", "userthree.amd@gmail.com"],
                    "Summary": "Team Meet"
                },
                {
                    "StartTime": "2025-07-17T13:00:00+05:30",
                    "EndTime": "2025-07-17T14:00:00+05:30",
                    "NumAttendees": 1,
                    "Attendees": ["SELF"],
                    "Summary": "Lunch with Customers"
                }
            ]
        }
        return mock_calendars.get(email, [])
    
    def create_participant_agents(self, attendees_data: List[Dict]) -> List[ParticipantAgent]:
        agents = []
        for attendee in attendees_data:
            email = attendee['email']
            calendar_events = attendee['events']
            preferences = USER_PREFERENCES.get(email, {
                'preferred_times': ['morning', 'afternoon'],
                'buffer_minutes': 15,
                'timezone': 'Asia/Kolkata',
                'avoid_lunch': True,
                'seniority_weight': 0.5
            })
            agent = ParticipantAgent(
                email=email,
                calendar_data=calendar_events,
                preferences=preferences,
                llm_client=self.llm
            )
            agents.append(agent)
            self.participants[email] = agent
        return agents
    
    async def schedule_meeting(self, meeting_request: Dict) -> Dict:
        try:
            logging.info("Original request: %s", meeting_request.get('Request_id', 'unknown'))
            transformed_request = self._transform_input_format(meeting_request)
            logging.info("Duration extracted: %s minutes", transformed_request['Duration_mins'])
            participants = self.create_participant_agents(transformed_request['Attendees'])
            logging.info("Created %d participant agents", len(participants))
            negotiation_result = await self.negotiator.negotiate_meeting(participants, transformed_request)
            
            if negotiation_result['success']:
                return self._format_success_response_correct_format(
                    negotiation_result, meeting_request, transformed_request
                )
            else:
                return self._format_failure_response_correct_format(
                    negotiation_result, meeting_request, transformed_request
                )
        except Exception as e:
            logging.error("Error in schedule_meeting: %s", e)
            import traceback
            traceback.print_exc()
            return self._format_error_response_correct_format(str(e), meeting_request)
    
    def _format_success_response_correct_format(self, result: Dict, original_request: Dict, transformed_request: Dict) -> Dict:
        scheduled_slot = result['scheduled_slot']
        new_event = {
            "StartTime": scheduled_slot['start_time'],
            "EndTime": scheduled_slot['end_time'],
            "NumAttendees": len(transformed_request['Attendees']),
            "Attendees": [att['email'] for att in transformed_request['Attendees']],
            "Summary": original_request.get('Subject', 'Meeting')
        }
        output_attendees = []
        for attendee_data in transformed_request['Attendees']:
            attendee_events = attendee_data['events'].copy()
            attendee_events.append(new_event)
            output_attendees.append({
                'email': attendee_data['email'],
                'events': attendee_events
            })
        return {
            'Request_id': original_request['Request_id'],
            'Datetime': original_request['Datetime'],
            'Location': original_request['Location'],
            'From': original_request['From'],
            'Attendees': output_attendees,
            'Subject': original_request['Subject'],
            'EmailContent': original_request['EmailContent'],
            'EventStart': scheduled_slot['start_time'],
            'EventEnd': scheduled_slot['end_time'],
            'Duration_mins': transformed_request['Duration_mins'],
            'MetaData': {
                'scheduling_decision': {
                    'chosen_slot': {
                        'time': scheduled_slot['display_time'],
                        'reason': f"Optimal time found for {len(output_attendees)} participants"
                    },
                    'conflicts_resolved': len(result.get('alternatives_considered', [])),
                    'success': True
                }
            }
        }
    
    def _format_failure_response_correct_format(self, result: Dict, original_request: Dict, transformed_request: Dict) -> Dict:
        output_attendees = []
        for attendee_data in transformed_request['Attendees']:
            output_attendees.append({
                'email': attendee_data['email'],
                'events': attendee_data['events']
            })
        return {
            'Request_id': original_request['Request_id'],
            'Datetime': original_request['Datetime'],
            'Location': original_request['Location'],
            'From': original_request['From'],
            'Attendees': output_attendees,
            'Subject': original_request['Subject'],
            'EmailContent': original_request['EmailContent'],
            'EventStart': None,
            'EventEnd': None,
            'Duration_mins': transformed_request['Duration_mins'],
            'MetaData': {
                'scheduling_decision': {
                    'chosen_slot': None,
                    'reason': f"No suitable slot found: {result['reason']}",
                    'success': False
                }
            },
            'error': 'No available time slot found'
        }
    
    def _format_error_response_correct_format(self, error: str, original_request: Dict) -> Dict:
        return {
            'Request_id': original_request.get('Request_id', 'unknown'),
            'error': f"Scheduling failed: {error}",
            'MetaData': {
                'scheduling_decision': {
                    'chosen_slot': None,
                    'reason': f"System error: {error}",
                    'success': False
                }
            }
        }
    
    async def get_system_status(self) -> Dict:
        try:
            llm_status = self.llm.health_check()
            return {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'llm_service': llm_status,
                    'calendar_service': {'status': 'healthy'},
                    'validator': {'status': 'healthy'},
                    'negotiator': {'status': 'healthy'}
                },
                'participants_loaded': len(self.participants)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
