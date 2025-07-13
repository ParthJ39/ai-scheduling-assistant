import re
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
import json

class EmailParser:
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)',
            r'(\d{1,2})\s*(AM|PM|am|pm)',
            r'at\s+(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)',
            r'at\s+(\d{1,2})\s*(AM|PM|am|pm)',
        ]
        
        self.duration_patterns = [
            r'(\d+)\s*(minutes?|mins?)',
            r'(\d+)\s*(hours?|hrs?)',
            r'for\s+(\d+)\s*(minutes?|mins?)',
            r'for\s+(\d+)\s*(hours?|hrs?)',
            r'(\d+)-minute',
            r'(\d+)-hour'
        ]

    def parse_email(self, email_content: str, request_datetime: str = None) -> Dict:
        if self.llm_service:
            try:
                llm_result = self._parse_with_llm(email_content, request_datetime)
                if llm_result:
                    return llm_result
            except Exception as e:
                print(f"LLM parsing failed: {e}")
        
        return self._parse_with_regex(email_content, request_datetime)
    
    def _parse_with_llm(self, email_content: str, request_datetime: str = None) -> Optional[Dict]:
        try:
            base_date = self._get_base_date(request_datetime)
            
            prompt = f"""Extract meeting details from this email sent on {base_date.strftime('%Y-%m-%d')}:
"{email_content}"

Calculate the actual meeting date based on relative references.
Today's date is {base_date.strftime('%Y-%m-%d')} ({base_date.strftime('%A')}).

Return exactly this JSON format:
{{
    "suggested_date": "YYYY-MM-DD",
    "suggested_time": "HH:MM", 
    "duration_minutes": 30,
    "urgency": "medium",
    "meeting_type": "discussion"
}}

Examples:
- If today is Tuesday and email says "next Thursday", return "2025-07-17"
- If email says "30 minutes", return duration_minutes: 30

Only return valid JSON, no other text."""
            
            print("Calling LLM for email parsing")
            response = self.llm_service.generate(prompt, max_tokens=120)
            print(f"LLM Response: {response}")
            
            response_clean = response.strip()
            
            if response_clean.startswith('```json'):
                response_clean = response_clean.replace('```json', '').replace('```', '')
            if response_clean.startswith('```'):
                response_clean = response_clean.replace('```', '')
            
            start_idx = response_clean.find('{')
            end_idx = response_clean.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_clean[start_idx:end_idx]
                parsed_result = json.loads(json_str)
                print(f"LLM parsing successful: {parsed_result}")
                return parsed_result
            else:
                print(f"No JSON found in LLM response: {response}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            print(f"LLM parsing failed: {e}")
            return None
    
    def _parse_with_regex(self, email_content: str, request_datetime: str = None) -> Dict:
        content_lower = email_content.lower()
        
        base_date = self._get_base_date(request_datetime)
        print(f"Base date for calculation: {base_date.strftime('%Y-%m-%d (%A)')}")
        
        suggested_time = self._extract_time(email_content)
        suggested_date = self._extract_date_with_calculation(email_content, base_date)
        duration_minutes = self._extract_duration(email_content)
        urgency = self._determine_urgency(email_content)
        meeting_type = self._determine_meeting_type(email_content)
        
        result = {
            'suggested_date': suggested_date,
            'suggested_time': suggested_time,
            'duration_minutes': duration_minutes,
            'urgency': urgency,
            'meeting_type': meeting_type
        }
        
        print(f"Regex parsing result: {result}")
        return result
    
    def _get_base_date(self, request_datetime: str = None) -> datetime:
        if request_datetime:
            try:
                if 'T' in request_datetime:
                    date_part = request_datetime.split('T')[0]
                    return datetime.strptime(date_part, '%d-%m-%Y')
                else:
                    for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            return datetime.strptime(request_datetime, fmt)
                        except ValueError:
                            continue
            except Exception as e:
                print(f"Error parsing request datetime {request_datetime}: {e}")
        
        return datetime.now()
    
    def _extract_date_with_calculation(self, content: str, base_date: datetime) -> str:
        content_lower = content.lower()
        
        print(f"Analyzing email content from base date {base_date.strftime('%Y-%m-%d (%A)')}")
        
        if 'tomorrow' in content_lower:
            target_date = base_date + timedelta(days=1)
            print(f"Found 'tomorrow' -> {target_date.strftime('%Y-%m-%d (%A)')}")
            return target_date.strftime('%Y-%m-%d')
        
        if 'today' in content_lower:
            print(f"Found 'today' -> {base_date.strftime('%Y-%m-%d (%A)')}")
            return base_date.strftime('%Y-%m-%d')
        
        if 'next week' in content_lower:
            days_until_next_monday = 7 - base_date.weekday()
            if days_until_next_monday == 7:
                days_until_next_monday = 7
            target_date = base_date + timedelta(days=days_until_next_monday)
            print(f"Found 'next week' -> {target_date.strftime('%Y-%m-%d (%A)')}")
            return target_date.strftime('%Y-%m-%d')
        
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in weekdays.items():
            next_day_pattern = f'next\\s+{day_name}'
            if re.search(next_day_pattern, content_lower):
                target_date = self._get_next_weekday(base_date, day_num)
                print(f"Found 'next {day_name}' -> {target_date.strftime('%Y-%m-%d (%A)')}")
                return target_date.strftime('%Y-%m-%d')
            
            elif re.search(f'\\b{day_name}\\b', content_lower) and 'next' not in content_lower:
                current_weekday = base_date.weekday()
                if day_num > current_weekday:
                    days_ahead = day_num - current_weekday
                else:
                    days_ahead = 7 - current_weekday + day_num
                
                target_date = base_date + timedelta(days=days_ahead)
                print(f"Found '{day_name}' -> {target_date.strftime('%Y-%m-%d (%A)')}")
                return target_date.strftime('%Y-%m-%d')
        
        if base_date.weekday() >= 4:
            days_ahead = 7 - base_date.weekday()
            target_date = base_date + timedelta(days=days_ahead)
        else:
            target_date = base_date + timedelta(days=1)
        
        print(f"Using default next business day -> {target_date.strftime('%Y-%m-%d (%A)')}")
        return target_date.strftime('%Y-%m-%d')
    
    def _get_next_weekday(self, base_date: datetime, target_weekday: int) -> datetime:
        current_weekday = base_date.weekday()
        
        if target_weekday >= current_weekday:
            days_ahead = 7 + (target_weekday - current_weekday)
        else:
            days_ahead = 7 - (current_weekday - target_weekday)
        
        return base_date + timedelta(days=days_ahead)
    
    def _extract_time(self, content: str) -> Optional[str]:
        for pattern in self.time_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                try:
                    if len(groups) >= 3:
                        hour = int(groups[0])
                        minute = int(groups[1])
                        period = groups[2].upper()
                        
                        if period == 'PM' and hour != 12:
                            hour += 12
                        elif period == 'AM' and hour == 12:
                            hour = 0
                            
                        return f"{hour:02d}:{minute:02d}"
                        
                    elif len(groups) >= 2:
                        hour = int(groups[0])
                        period = groups[1].upper()
                        
                        if period == 'PM' and hour != 12:
                            hour += 12
                        elif period == 'AM' and hour == 12:
                            hour = 0
                            
                        return f"{hour:02d}:00"
                        
                except (ValueError, IndexError) as e:
                    print(f"Time parsing error: {e}")
                    continue
        
        return None
    
    def _extract_duration(self, content: str) -> int:
        for pattern in self.duration_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    number = int(groups[0])
                    unit = groups[1].lower() if len(groups) > 1 else 'minutes'
                    
                    if 'hour' in unit:
                        return number * 60
                    else:
                        return number
                except (ValueError, IndexError):
                    continue
        
        return 30
    
    def _determine_urgency(self, content: str) -> str:
        content_lower = content.lower()
        
        urgent_keywords = ['urgent', 'asap', 'immediately', 'emergency', 'critical']
        high_keywords = ['important', 'priority', 'deadline', 'soon']
        
        if any(keyword in content_lower for keyword in urgent_keywords):
            return 'high'
        elif any(keyword in content_lower for keyword in high_keywords):
            return 'medium'
        else:
            return 'low'
    
    def _determine_meeting_type(self, content: str) -> str:
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['standup', 'daily', 'scrum']):
            return 'standup'
        elif any(keyword in content_lower for keyword in ['review', 'retrospective', 'demo']):
            return 'review'
        elif any(keyword in content_lower for keyword in ['planning', 'brainstorm', 'strategy']):
            return 'planning'
        else:
            return 'other'