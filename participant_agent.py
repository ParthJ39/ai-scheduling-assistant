import asyncio
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any
from llm_service import LLMService
from metadata_framework import record_participant

class ParticipantAgent:
    def __init__(self, email: str, calendar_data: List[Dict], preferences: Dict, llm_client=None):
        self.email = email
        self.calendar = calendar_data
        self.preferences = preferences
        self.llm = llm_client or LLMService()
        self.timezone = pytz.timezone(preferences.get('timezone', 'Asia/Kolkata'))
        self._working_hours_cache = {}
        
    def find_available_slots(self, date_str: str, duration_mins: int) -> List[Dict]:
        available_slots = []
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        cache_key = target_date.isoformat()
        if cache_key in self._working_hours_cache:
            working_start, working_end = self._working_hours_cache[cache_key]
        else:
            working_start, working_end = self._get_working_hours_from_calendar(target_date)
            self._working_hours_cache[cache_key] = (working_start, working_end)
        
        current_time = working_start
        while current_time + timedelta(minutes=duration_mins) <= working_end:
            slot_end = current_time + timedelta(minutes=duration_mins)
            
            if not self._has_conflict(current_time, slot_end):
                preference_score = self._calculate_preference_score(current_time)
                available_slots.append({
                    'start_time': current_time.isoformat(),
                    'end_time': slot_end.isoformat(),
                    'preference_score': preference_score,
                    'participant': self.email
                })
            
            current_time += timedelta(minutes=30)
        
        return sorted(available_slots, key=lambda x: x['preference_score'], reverse=True)[:10]
    
    def _get_working_hours_from_calendar(self, target_date):
        default_start = self.timezone.localize(datetime.combine(target_date, datetime.min.time().replace(hour=9)))
        default_end = self.timezone.localize(datetime.combine(target_date, datetime.min.time().replace(hour=18)))
        
        for event in self.calendar:
            if 'Off Hours' in event.get('Summary', ''):
                event_start = datetime.fromisoformat(event['StartTime'].replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(event['EndTime'].replace('Z', '+00:00'))
                
                if event_start.tzinfo != self.timezone:
                    event_start = event_start.astimezone(self.timezone)
                    event_end = event_end.astimezone(self.timezone)
                
                if event_start.date() <= target_date <= event_end.date():
                    if event_end.date() == target_date and event_end.hour <= 12:
                        default_start = max(default_start, event_end)
                    if event_start.date() == target_date and event_start.hour >= 12:
                        default_end = min(default_end, event_start)
        
        return default_start, default_end
    
    def _has_conflict(self, start_time: datetime, end_time: datetime) -> bool:
        for event in self.calendar:
            event_start = datetime.fromisoformat(event['StartTime'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['EndTime'].replace('Z', '+00:00'))
            
            if event_start.tzinfo != start_time.tzinfo:
                event_start = event_start.astimezone(start_time.tzinfo)
                event_end = event_end.astimezone(start_time.tzinfo)
            
            buffer_mins = 5 if 'Off Hours' in event.get('Summary', '') else 10
            buffered_start = start_time - timedelta(minutes=buffer_mins)
            buffered_end = end_time + timedelta(minutes=buffer_mins)
            
            if not (buffered_end <= event_start or buffered_start >= event_end):
                return True
        
        return False
    
    def _calculate_preference_score(self, start_time: datetime) -> float:
        score = 0.5
        hour = start_time.hour
        
        preferred_times = self.preferences.get('preferred_times', [])
        if 'morning' in preferred_times and 9 <= hour < 12:
            score += 0.3
        elif 'afternoon' in preferred_times and 13 <= hour < 17:
            score += 0.3
        
        if self.preferences.get('avoid_lunch', False) and 12 <= hour < 14:
            score -= 0.3
        
        seniority = self.preferences.get('seniority_weight', 0.5)
        score = score * (0.8 + 0.4 * seniority)
        
        return max(0, min(1, score))
    
    async def evaluate_proposal(self, proposed_slot: Dict, context: str = "", urgency: str = "medium") -> Dict:
        start_time = datetime.fromisoformat(proposed_slot['start_time'])
        end_time = datetime.fromisoformat(proposed_slot['end_time'])
        
        if self._has_conflict(start_time, end_time):
            conflict_type = "meeting conflict"
            for event in self.calendar:
                event_start = datetime.fromisoformat(event['StartTime'].replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(event['EndTime'].replace('Z', '+00:00'))
                
                if event_start.tzinfo != start_time.tzinfo:
                    event_start = event_start.astimezone(start_time.tzinfo)
                    event_end = event_end.astimezone(start_time.tzinfo)
                
                if not (end_time <= event_start or start_time >= event_end):
                    if 'Off Hours' in event.get('Summary', ''):
                        conflict_type = "outside working hours"
                    else:
                        conflict_type = f"conflicts with {event['Summary']}"
                    break
            
            if urgency in ['urgent', 'high'] and 'outside working hours' in conflict_type:
                decision = 'CONDITIONAL_ACCEPT'
                reasoning = f"Can accommodate this {urgency} request outside normal hours"
            else:
                decision = 'REJECT'
                reasoning = f"Cannot attend - {conflict_type}"
            
            record_participant(
                participant_id=self.email,
                decision=decision,
                reasoning=reasoning,
                conflict_details=conflict_type
            )
            
            return {
                'decision': decision,
                'reason': 'conflict',
                'preference_score': 0.2 if decision == 'CONDITIONAL_ACCEPT' else 0,
                'detailed_reasoning': reasoning
            }
        
        preference_score = self._calculate_preference_score(start_time)
        hour = start_time.hour
        
        if preference_score >= 0.7:
            if 9 <= hour < 12:
                reasoning = "Perfect timing - this works great with my morning schedule"
            else:
                reasoning = "This time works excellently with my preferences"
            decision = 'ACCEPT'
        elif preference_score >= 0.4:
            reasoning = "This time is workable for me"
            decision = 'CONDITIONAL_ACCEPT'
        else:
            if hour < 9:
                reasoning = "Too early for my schedule preferences"
            elif hour > 17:
                reasoning = "Too late in the day for me"
            else:
                reasoning = "This time doesn't align well with my preferences"
            decision = 'REJECT'
        
        record_participant(
            participant_id=self.email,
            decision=decision,
            reasoning=reasoning,
            conflict_details=None
        )
        
        return {
            'decision': decision,
            'reason': 'preference_based',
            'preference_score': preference_score,
            'participant': self.email,
            'timezone': str(self.timezone),
            'detailed_reasoning': reasoning
        }
    
    async def suggest_alternatives(self, target_date, duration_mins: int, urgency: str = "medium") -> List[Dict]:
        available_slots = self.find_available_slots(target_date.strftime("%Y-%m-%d"), duration_mins)
        
        if urgency in ['urgent', 'high'] and len(available_slots) < 3:
            extended_slots = self._find_extended_slots(target_date, duration_mins)
            available_slots.extend(extended_slots)
        
        alternatives = []
        for slot in available_slots[:3]:
            start_dt = datetime.fromisoformat(slot['start_time'])
            
            if 9 <= start_dt.hour < 12:
                reasoning = "Good morning time for focused discussion"
            elif 13 <= start_dt.hour < 17:
                reasoning = "Productive afternoon slot"
            else:
                reasoning = "Available time that could work"
            
            alternatives.append({
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'preference_score': slot['preference_score'],
                'time_display': f"{start_dt.strftime('%H:%M')} IST",
                'reasoning': reasoning
            })
        
        return alternatives
    
    def _find_extended_slots(self, target_date, duration_mins: int) -> List[Dict]:
        extended_slots = []
        
        for hour in [7, 8, 18]:
            start_time = self.timezone.localize(
                datetime.combine(target_date, datetime.min.time().replace(hour=hour))
            )
            end_time = start_time + timedelta(minutes=duration_mins)
            
            if not self._has_conflict(start_time, end_time):
                extended_slots.append({
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'preference_score': 0.4,
                    'participant': self.email,
                    'is_extended_hours': True
                })
        
        return extended_slots