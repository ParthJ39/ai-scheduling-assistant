import time
import uuid
from datetime import datetime
from typing import Dict, List, Any

class BusinessMetadata:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.agent_interactions = []
        
    def record_interaction(self, agent: str, action: str, outcome: str, reasoning: str):
        interaction = f"{agent.title()}: {action} - {outcome}. {reasoning}"
        self.agent_interactions.append(interaction)
    
    def generate_business_summary(self) -> List[str]:
        return self.agent_interactions

_business_metadata = None

def get_business_metadata() -> BusinessMetadata:
    global _business_metadata
    if _business_metadata is None:
        _business_metadata = BusinessMetadata()
    return _business_metadata

def reset_business_metadata():
    global _business_metadata
    _business_metadata = BusinessMetadata()

def record_coordinator(action: str, outcome: str, reasoning: str):
    get_business_metadata().record_interaction("Coordinator", action, outcome, reasoning)

def record_negotiator(action: str, outcome: str, reasoning: str):
    get_business_metadata().record_interaction("Negotiator", action, outcome, reasoning)

def record_participant(participant_id: str, decision: str, reasoning: str, conflict_details: str = None):
    participant_name = participant_id.split('@')[0].title()
    clean_reasoning = reasoning.replace('preference score', 'schedule preference')
    clean_reasoning = clean_reasoning.replace('buffer minutes', 'transition time')
    interaction = f"{participant_name}: {decision} - {clean_reasoning}"
    get_business_metadata().agent_interactions.append(interaction)

def record_selection(selected_slot: Dict, reasoning: str):
    get_business_metadata().record_interaction("Scheduler", "finalized meeting time", 
                                             f"selected {selected_slot['time_display']}", reasoning)

def record_request(request_data: Dict):
    attendees = request_data.get('Attendees', [])
    email_content = request_data.get('EmailContent', '')
    subject = request_data.get('Subject', 'Meeting')
    
    get_business_metadata().record_interaction("System", "received meeting request", 
                                             f"processed request for {len(attendees)} participants", 
                                             f"Meeting subject: {subject}")