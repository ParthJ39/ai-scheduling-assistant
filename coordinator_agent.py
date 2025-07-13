import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pytz
import re
from participant_agent import ParticipantAgent
from negotiator_agent import NegotiatorAgent
from llm_service import LLMService
from json_validator import JSONValidator
from metadata_framework import record_coordinator, record_request, get_business_metadata, reset_business_metadata

import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def retrieve_calendar_events(user, start, end):
    events_list = []
    try:
        token_path = "../Keys/"+user.split("@")[0]+".token"
        user_creds = Credentials.from_authorized_user_file(token_path)
        calendar_service = build("calendar", "v3", credentials=user_creds)
        events_result = calendar_service.events().list(
            calendarId='primary', 
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        target_date = start_dt.date()
        
        for event in events: 
            attendee_list = []
            try:
                for attendee in event["attendees"]: 
                    attendee_list.append(attendee['email'])
            except: 
                attendee_list.append("SELF")
            
            start_time = event["start"]["dateTime"]
            end_time = event["end"]["dateTime"]
            summary = event["summary"]
            
            event_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            if not (event_end.date() < target_date or event_start.date() > target_date):
                events_list.append({
                    "StartTime": start_time, 
                    "EndTime": end_time, 
                    "NumAttendees": len(set(attendee_list)), 
                    "Attendees": list(set(attendee_list)),
                    "Summary": summary
                })
        
        events_list.sort(key=lambda x: x["StartTime"])
                
    except Exception as e:
        print(f"Failed to retrieve calendar for {user}: {e}")
        events_list = []
    
    print(f"Retrieved {len(events_list)} events for {user}")
    return events_list

class CoordinatorAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client or LLMService()
        self.negotiator = NegotiatorAgent(self.llm)
        self.validator = JSONValidator()
        self.participants = {}
        self.calendar_cache = {}
        self.user_preferences = {
            "userthree.amd@gmail.com": {
                "preferred_times": ["morning"],
                "buffer_minutes": 15,
                "timezone": "Asia/Kolkata",
                "max_meeting_length": 60,
                "avoid_lunch": True,
                "seniority_weight": 0.7
            },
            "userone.amd@gmail.com": {
                "preferred_times": ["morning", "afternoon"],
                "buffer_minutes": 10,
                "timezone": "Asia/Kolkata",
                "max_meeting_length": 90,
                "avoid_lunch": True,
                "seniority_weight": 0.6
            },
            "usertwo.amd@gmail.com": {
                "preferred_times": ["afternoon"],
                "buffer_minutes": 20,
                "timezone": "Asia/Kolkata",
                "max_meeting_length": 75,
                "avoid_lunch": False,
                "seniority_weight": 0.5
            }
        }
        
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
                try:
                    number = int(match.group(1))
                    if 'hour' in pattern or 'hr' in pattern:
                        number *= 60
                    return str(number)
                except (ValueError, IndexError):
                    continue
        
        return "30"
    
    def _extract_target_date_from_email(self, email_content: str, email_datetime: str = None) -> str:
        if email_datetime:
            try:
                if 'T' in email_datetime:
                    date_part = email_datetime.split('T')[0]
                    if '-' in date_part:
                        parts = date_part.split('-')
                        if len(parts[0]) == 4:
                            reference_date = datetime.strptime(date_part, '%Y-%m-%d')
                        else:
                            reference_date = datetime.strptime(date_part, '%d-%m-%Y')
                    else:
                        reference_date = datetime.now()
                else:
                    reference_date = datetime.now()
            except:
                reference_date = datetime.now()
        else:
            reference_date = datetime.now()
        
        print(f"Reference date for parsing: {reference_date.strftime('%Y-%m-%d (%A)')}")
        
        content_lower = email_content.lower()
        
        if 'tomorrow' in content_lower:
            target_date = reference_date + timedelta(days=1)
            return target_date.strftime('%Y-%m-%d')
        
        if 'today' in content_lower:
            return reference_date.strftime('%Y-%m-%d')
        
        if 'next week' in content_lower:
            days_until_monday = (7 - reference_date.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            target_date = reference_date + timedelta(days=days_until_monday)
            return target_date.strftime('%Y-%m-%d')
        
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(weekdays):
            if f'next {day}' in content_lower:
                current_weekday = reference_date.weekday()
                target_weekday = i
                
                if target_weekday > current_weekday:
                    days_ahead = target_weekday - current_weekday
                else:
                    days_ahead = 7 - current_weekday + target_weekday
                
                target_date = reference_date + timedelta(days=days_ahead)
                
                print(f"Calculated 'next {day}': {target_date.strftime('%Y-%m-%d (%A)')}")
                return target_date.strftime('%Y-%m-%d')
        
        for i, day in enumerate(weekdays):
            if day in content_lower and f'next {day}' not in content_lower:
                current_weekday = reference_date.weekday()
                target_weekday = i
                
                if target_weekday >= current_weekday:
                    days_ahead = target_weekday - current_weekday
                else:
                    days_ahead = 7 - current_weekday + target_weekday
                
                target_date = reference_date + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')
        
        tomorrow = reference_date + timedelta(days=1)
        return tomorrow.strftime('%Y-%m-%d')
    
    def _get_calendar_events_cached(self, email: str, start_datetime: str, end_datetime: str) -> List[Dict]:
        cache_key = f"{email}_{start_datetime}_{end_datetime}"
        
        if cache_key in self.calendar_cache:
            print(f"Using cached calendar data for {email}")
            return self.calendar_cache[cache_key]
        
        print(f"Fetching calendar data for {email}")
        real_events = retrieve_calendar_events(email, start_datetime, end_datetime)
        
        self.calendar_cache[cache_key] = real_events
        return real_events
    
    def _filter_relevant_events(self, events: List[Dict], target_date: str) -> List[Dict]:
        filtered_events = []
        target_dt = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        for event in events:
            event_start = datetime.fromisoformat(event['StartTime'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['EndTime'].replace('Z', '+00:00'))
            
            if event_start.date() <= target_dt <= event_end.date():
                filtered_events.append(event)
        
        return filtered_events
    
    def _transform_input_format(self, meeting_request: Dict) -> Dict:
        email_content = meeting_request.get('EmailContent', '')
        email_datetime = meeting_request.get('Datetime', '')
        duration_mins = self._extract_duration_from_email(email_content)
        
        from_email = meeting_request.get('From', '')
        attendee_emails = [att.get('email') for att in meeting_request.get('Attendees', [])]
        
        if from_email and from_email not in attendee_emails:
            attendee_emails.append(from_email)
        
        attendee_emails = list(set(attendee_emails))
        
        target_date = self._extract_target_date_from_email(email_content, email_datetime)
        start_datetime = f"{target_date}T00:00:00+05:30"
        end_datetime = f"{target_date}T23:59:59+05:30"
        
        print(f"Target date extracted: {target_date}")
        print(f"Looking up calendar events for date range: {start_datetime} to {end_datetime}")
        
        transformed_attendees = []
        
        for email in attendee_emails:
            real_events = self._get_calendar_events_cached(email, start_datetime, end_datetime)
            
            if not real_events:
                print(f"No real calendar data for {email}, events will be empty")
                real_events = []
            
            filtered_events = self._filter_relevant_events(real_events, target_date)
            
            transformed_attendees.append({
                'email': email,
                'events': filtered_events
            })
        
        transformed_request = meeting_request.copy()
        transformed_request['Duration_mins'] = duration_mins
        transformed_request['Attendees'] = transformed_attendees
        
        return transformed_request
    
    def create_participant_agents(self, attendees_data: List[Dict]) -> List[ParticipantAgent]:
        agents = []
        
        for attendee in attendees_data:
            email = attendee['email']
            calendar_events = attendee['events']
            
            preferences = self.user_preferences.get(email, {
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
            self.calendar_cache.clear()
            reset_business_metadata()
            
            record_request(meeting_request)
            
            request_id = meeting_request.get('Request_id', 'unknown')
            attendees = meeting_request.get('Attendees', [])
            email_content = meeting_request.get('EmailContent', '')
            
            print(f"Processing request: {request_id}")
            
            record_coordinator(
                action="parse meeting requirements",
                outcome=f"extracted details for {len(attendees)} attendees",
                reasoning="Analyzed email content to understand meeting constraints and participant needs"
            )
            
            transformed_request = self._transform_input_format(meeting_request)
            duration_extracted = transformed_request['Duration_mins']
            
            print(f"Duration extracted: {duration_extracted} minutes")
            
            record_coordinator(
                action="create scheduling assistants", 
                outcome=f"set up {len(attendees)} specialized agents",
                reasoning="Each participant needs personalized scheduling logic based on their preferences and calendar"
            )
            
            participants = self.create_participant_agents(transformed_request['Attendees'])
            print(f"Created {len(participants)} participant agents")
            
            record_coordinator(
                action="initiate negotiation process",
                outcome="handed off to negotiation specialist",
                reasoning="Negotiator will find optimal time by balancing all participant constraints and preferences"
            )
            
            negotiation_result = await self.negotiator.negotiate_meeting(participants, transformed_request)
            
            if negotiation_result['success']:
                scheduled_time = negotiation_result['scheduled_slot']['start_time']
                
                record_coordinator(
                    action="finalize successful scheduling",
                    outcome=f"confirmed meeting for {scheduled_time}",
                    reasoning="All participants confirmed availability and the optimal time was selected"
                )
                
                response = self._format_success_response_correct_format(
                    negotiation_result, meeting_request, transformed_request
                )
                return response
                
            else:
                failure_reason = negotiation_result['reason']
                
                record_coordinator(
                    action="handle scheduling failure",
                    outcome="no suitable time found",
                    reasoning=f"Unable to resolve conflicts: {failure_reason}"
                )
                
                response = self._format_failure_response_correct_format(
                    negotiation_result, meeting_request, transformed_request
                )
                return response
                
        except Exception as e:
            record_coordinator(
                action="handle system error",
                outcome="scheduling failed with error",
                reasoning=f"Unexpected system error prevented completion: {str(e)}"
            )
            
            print(f"Error in schedule_meeting: {e}")
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
        
        business_summary_lines = get_business_metadata().generate_business_summary()
        
        response = {
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
                'agent_reasoning_summary': business_summary_lines
            }
        }
        
        return response
    
    def _format_failure_response_correct_format(self, result: Dict, original_request: Dict, transformed_request: Dict) -> Dict:
        output_attendees = []
        for attendee_data in transformed_request['Attendees']:
            output_attendees.append({
                'email': attendee_data['email'],
                'events': attendee_data['events']
            })
        
        business_summary_lines = get_business_metadata().generate_business_summary()
        
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
                'agent_reasoning_summary': business_summary_lines
            },
            'error': 'No available time slot found'
        }
    
    def _format_error_response_correct_format(self, error: str, original_request: Dict) -> Dict:
        business_summary_lines = get_business_metadata().generate_business_summary()
        
        return {
            'Request_id': original_request.get('Request_id', 'unknown'),
            'error': f"Scheduling failed: {error}",
            'MetaData': {
                'agent_reasoning_summary': business_summary_lines
            }
        }