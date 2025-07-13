from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

class EmailParsingResult(BaseModel):
    suggested_date: str = Field(description="Meeting date in YYYY-MM-DD format")
    suggested_time: Optional[str] = Field(default=None, description="Meeting time in HH:MM format (24-hour)")
    duration_minutes: int = Field(default=30, description="Meeting duration in minutes")
    urgency: Literal['low', 'medium', 'high'] = Field(default='low', description="Meeting urgency level")
    meeting_type: Literal['standup', 'review', 'planning', 'one_on_one', 'interview', 'other'] = Field(default='other')

class CalendarEvent(BaseModel):
    StartTime: str = Field(description="Event start time in ISO format")
    EndTime: str = Field(description="Event end time in ISO format") 
    NumAttendees: int = Field(description="Number of attendees")
    Attendees: List[str] = Field(description="List of attendee emails")
    Summary: str = Field(description="Event title/summary")

class Attendee(BaseModel):
    email: str = Field(description="Attendee email address")
    events: List[CalendarEvent] = Field(default=[], description="Attendee's calendar events")

class MeetingRequest(BaseModel):
    Request_id: str = Field(description="Unique request identifier")
    Datetime: str = Field(description="Request timestamp")
    Location: str = Field(description="Meeting location")
    From: str = Field(description="Requester email")
    Attendees: List[Attendee] = Field(description="Meeting attendees with calendar data")
    Subject: str = Field(description="Meeting subject")
    EmailContent: str = Field(description="Original email content")
    Duration_mins: str = Field(description="Meeting duration in minutes")
    target_date: str = Field(description="Target meeting date")

class TimeSlot(BaseModel):
    start_time: str = Field(description="Slot start time in ISO format")
    end_time: str = Field(description="Slot end time in ISO format")
    duration_minutes: int = Field(description="Slot duration in minutes")
    participants: List[str] = Field(description="Participant emails")
    preference_score: Optional[float] = Field(default=None, description="Preference score 0-1")
    timezone_fairness: Optional[float] = Field(default=None, description="Timezone fairness score 0-1")
    overall_score: Optional[float] = Field(default=None, description="Overall suitability score 0-1")
    time_display: Optional[str] = Field(default=None, description="Human-readable time display")

class ParticipantEvaluation(BaseModel):
    participant: str = Field(description="Participant email")
    decision: Literal['ACCEPT', 'REJECT', 'CONDITIONAL_ACCEPT'] = Field(description="Decision on time slot")
    reason: str = Field(description="Reason for decision")
    preference_score: float = Field(description="Preference score 0-1")
    timezone: str = Field(description="Participant timezone")
    llm_reasoning: str = Field(description="LLM-generated reasoning")
    alternative_suggestions: Optional[List[TimeSlot]] = Field(default=None, description="Alternative time suggestions")

class NegotiationResult(BaseModel):
    success: bool = Field(description="Whether scheduling was successful")
    scheduled_slot: Optional[TimeSlot] = Field(default=None, description="Selected time slot if successful")
    alternatives_considered: List[TimeSlot] = Field(default=[], description="Alternative slots evaluated")
    evaluations: List[ParticipantEvaluation] = Field(default=[], description="Participant evaluations")
    conflicts: List[Dict[str, Any]] = Field(default=[], description="Scheduling conflicts encountered")
    consensus_score: float = Field(default=0.0, description="Overall consensus score 0-1")
    selection_reasoning: str = Field(default="", description="Reasoning for final selection")
    reason: Optional[str] = Field(default=None, description="Failure reason if unsuccessful")

class UserPreferences(BaseModel):
    preferred_times: List[str] = Field(default=['morning', 'afternoon'], description="Preferred meeting times")
    buffer_minutes: int = Field(default=15, description="Buffer time between meetings")
    timezone: str = Field(default='Asia/Kolkata', description="User timezone")
    max_meeting_length: int = Field(default=120, description="Maximum meeting duration in minutes")
    avoid_lunch: bool = Field(default=True, description="Avoid lunch hours")
    seniority_weight: float = Field(default=0.5, description="Seniority weight for prioritization")
    avoid_back_to_back: bool = Field(default=True, description="Avoid back-to-back meetings")

class SchedulingResponse(BaseModel):
    Request_id: str
    Datetime: str
    Location: str
    From: str
    Attendees: List[Attendee]
    Subject: str
    EmailContent: str
    EventStart: Optional[str] = None
    EventEnd: Optional[str] = None
    Duration_mins: str
    MetaData: Dict[str, Any]
    error: Optional[str] = None