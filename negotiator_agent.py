import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from llm_service import LLMService
from email_parser import EmailParser
import pytz
from metadata_framework import record_negotiator, record_selection

class NegotiatorAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client or LLMService()
        self.email_parser = EmailParser(llm_client)
        self.default_timezone = pytz.timezone('Asia/Kolkata')
    
    def _extract_urgency_from_email(self, email_content: str) -> str:
        content_lower = email_content.lower()
        
        urgent_keywords = ['urgent', 'asap', 'immediately', 'emergency', 'critical', 'rush']
        high_keywords = ['important', 'priority', 'soon', 'deadline', 'time-sensitive']
        low_keywords = ['when convenient', 'sometime', 'no rush', 'flexible']
        
        if any(keyword in content_lower for keyword in urgent_keywords):
            return 'urgent'
        elif any(keyword in content_lower for keyword in high_keywords):
            return 'high'
        elif any(keyword in content_lower for keyword in low_keywords):
            return 'low'
        else:
            return 'medium'
    
    async def negotiate_meeting(self, participants: List, meeting_request: Dict) -> Dict:
        duration_mins = int(meeting_request.get('Duration_mins', 30))
        email_content = meeting_request.get('EmailContent', '')
        
        urgency = self._extract_urgency_from_email(email_content)
        
        print(f"Negotiation started: {len(participants)} participants, urgency: {urgency}")
        
        record_negotiator(
            action="analyze meeting requirements",
            outcome=f"identified {urgency} priority meeting",
            reasoning="Analyzed email content for urgency level and time requirements"
        )
        
        parsed_email = self.email_parser.parse_email(email_content)
        target_date = parsed_email.get('suggested_date', self._get_default_date())
        requested_time = self._build_requested_time(parsed_email, target_date, duration_mins)
        
        print(f"Target date from email parsing: {target_date}")
        
        if requested_time and requested_time.get('start'):
            print("Evaluating specifically requested time")
            initial_result = await self._evaluate_specific_time_with_urgency(
                participants, requested_time, duration_mins, urgency, email_content
            )
            
            if initial_result['success']:
                requested_time_display = datetime.fromisoformat(requested_time['start']).strftime('%I:%M %p')
                
                record_negotiator(
                    action="confirm requested time",
                    outcome=f"success - {requested_time_display} works for everyone",
                    reasoning="User's preferred time was accommodated by all participants"
                )
                
                record_selection(
                    selected_slot={
                        'time_display': requested_time_display,
                        'start_time': requested_time['start'],
                        'end_time': requested_time['end']
                    },
                    reasoning=f"Selected {requested_time_display} as specifically requested. {urgency.title()} priority meeting successfully scheduled with all {len(participants)} participants agreeing to accommodate."
                )
                
                return self._create_success_response(initial_result, meeting_request, [])
            
            if urgency in ['urgent', 'high']:
                print("Attempting urgent time negotiation")
                negotiated_result = await self._negotiate_urgent_time(
                    participants, requested_time, duration_mins, urgency, email_content
                )
                
                if negotiated_result['success']:
                    return self._create_success_response(negotiated_result, meeting_request, [])
        
        print("Finding alternative time slots with urgency consideration")
        record_negotiator(
            action="search for available times",
            outcome="scanning participant calendars",
            reasoning="Finding times that work for all participants"
        )
        
        alternative_slots = await self._find_alternative_slots_with_urgency(
            participants, target_date, duration_mins, urgency
        )
        
        print(f"Alternative slots found: {len(alternative_slots)}")
        for i, slot in enumerate(alternative_slots[:3]):
            print(f"   {i+1}. {slot['time_display']} (score: {slot['overall_score']:.2f})")
        
        if not alternative_slots:
            if urgency in ['urgent', 'high']:
                print("No standard slots found - attempting extended urgency negotiation")
                extended_result = await self._extended_urgency_negotiation(
                    participants, target_date, duration_mins, urgency, email_content
                )
                
                if extended_result['success']:
                    return self._create_success_response(extended_result, meeting_request, [])
            
            record_negotiator(
                action="complete comprehensive search",
                outcome="no viable time slots found",
                reasoning="Exhaustive analysis including off-hours negotiations found no acceptable times"
            )
            
            return self._create_failure_response(meeting_request, f"No available slots found despite {urgency} priority")
        
        best_slot = await self._negotiate_best_slot_with_urgency(
            participants, alternative_slots, urgency, email_content
        )
        
        if not best_slot:
            return self._create_failure_response(meeting_request, "Could not achieve acceptable consensus")
        
        selected_time = best_slot['slot']['time_display']
        selection_reasoning = self._create_urgency_aware_selection_reasoning(
            best_slot, alternative_slots, participants, urgency
        )
        
        record_negotiator(
            action="select optimal time with urgency consideration",
            outcome=f"chose {selected_time} as best option for {urgency} priority meeting",
            reasoning="Balanced urgency requirements with participant availability and preferences"
        )
        
        record_selection(
            selected_slot={
                'time_display': selected_time,
                'start_time': best_slot['slot']['start_time'],
                'end_time': best_slot['slot']['end_time']
            },
            reasoning=selection_reasoning
        )
        
        return self._create_success_response(best_slot, meeting_request, alternative_slots)
    
    async def _evaluate_specific_time_with_urgency(self, participants: List, requested_time: Dict, 
                                                 duration_mins: int, urgency: str, context: str) -> Dict:
        evaluations = []
        conflicts = []
        
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal(
                    requested_time, 
                    context=context, 
                    urgency=urgency
                )
                evaluations.append(evaluation)
                
                if evaluation['decision'] == 'REJECT':
                    conflicts.append({
                        'participant': participant.email,
                        'reason': evaluation['reason'],
                        'urgency_considered': urgency
                    })
            except Exception as e:
                print(f"Error evaluating proposal for {participant.email}: {e}")
                evaluations.append({
                    'decision': 'REJECT',
                    'reason': 'evaluation_failed',
                    'preference_score': 0,
                    'participant': participant.email,
                    'urgency_considered': urgency
                })
                conflicts.append({
                    'participant': participant.email,
                    'reason': 'evaluation_failed',
                    'urgency_considered': urgency
                })
        
        success = len(conflicts) == 0
        consensus_score = sum(e.get('preference_score', 0) for e in evaluations) / len(evaluations) if evaluations else 0
        
        return {
            'success': success,
            'slot': {
                'start_time': requested_time['start'],
                'end_time': requested_time['end'],
                'time_display': self._format_time_display(requested_time['start'])
            },
            'evaluations': evaluations,
            'conflicts': conflicts,
            'consensus_score': consensus_score,
            'urgency_level': urgency
        }
    
    async def _negotiate_urgent_time(self, participants: List, requested_time: Dict, 
                                   duration_mins: int, urgency: str, context: str) -> Dict:
        print(f"Initiating urgent negotiation for {urgency} priority meeting")
        
        urgent_evaluations = []
        accommodations = []
        
        for participant in participants:
            try:
                urgent_evaluation = await participant.evaluate_proposal(
                    requested_time,
                    context=f"URGENT REQUEST: {context}. Please consider if you can accommodate this urgent meeting despite conflicts.",
                    urgency='urgent'
                )
                
                urgent_evaluations.append(urgent_evaluation)
                
                if urgent_evaluation['decision'] in ['ACCEPT', 'CONDITIONAL_ACCEPT']:
                    accommodations.append({
                        'participant': participant.email,
                        'decision': urgent_evaluation['decision'],
                        'conditions': urgent_evaluation.get('conditions', None)
                    })
                    
            except Exception as e:
                print(f"Urgent evaluation failed for {participant.email}: {e}")
                continue
        
        acceptance_rate = len([e for e in urgent_evaluations if e['decision'] in ['ACCEPT', 'CONDITIONAL_ACCEPT']]) / len(urgent_evaluations)
        
        if acceptance_rate >= 0.8:
            record_negotiator(
                action="successful urgent negotiation",
                outcome=f"achieved {acceptance_rate:.1%} accommodation for urgent meeting",
                reasoning="Participants agreed to accommodate urgent request despite initial conflicts"
            )
            
            return {
                'success': True,
                'slot': {
                    'start_time': requested_time['start'],
                    'end_time': requested_time['end'],
                    'time_display': self._format_time_display(requested_time['start'])
                },
                'evaluations': urgent_evaluations,
                'accommodations': accommodations,
                'consensus_score': acceptance_rate,
                'negotiation_type': 'urgent_accommodation'
            }
        
        return {'success': False, 'reason': 'Urgent negotiation failed to achieve sufficient accommodation'}
    
    async def _find_alternative_slots_with_urgency(self, participants: List, target_date: str, 
                                                 duration_mins: int, urgency: str) -> List[Dict]:
        all_available_slots = {}
        
        print(f"Getting slots from {len(participants)} participants for {target_date}")
        
        for participant in participants:
            try:
                if urgency in ['urgent', 'high']:
                    slots = await participant.suggest_alternatives(
                        datetime.strptime(target_date, '%Y-%m-%d').date(), 
                        duration_mins, 
                        urgency=urgency
                    )
                else:
                    slots = participant.find_available_slots(target_date, duration_mins)
                
                all_available_slots[participant.email] = slots
                print(f"  {participant.email}: {len(slots)} slots available")
                
            except Exception as e:
                print(f"Error getting slots for {participant.email}: {e}")
                all_available_slots[participant.email] = []
        
        common_slots = self._find_common_slots_fixed(all_available_slots, urgency)
        print(f"Found {len(common_slots)} common slots after intersection")
        
        scored_slots = []
        for slot in common_slots:
            try:
                consensus_score = await self._calculate_consensus_fast(participants, slot, urgency)
                urgency_bonus = self._calculate_urgency_bonus(slot, urgency)
                
                scored_slots.append({
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                    'consensus_score': consensus_score,
                    'urgency_bonus': urgency_bonus,
                    'overall_score': consensus_score + urgency_bonus,
                    'time_display': self._format_time_display(slot['start_time'])
                })
            except Exception as e:
                print(f"Error scoring slot: {e}")
                continue
        
        final_slots = sorted(scored_slots, key=lambda x: x['overall_score'], reverse=True)[:10]
        print(f"Returning {len(final_slots)} scored and ranked slots")
        
        return final_slots
    
    def _find_common_slots_fixed(self, all_slots: Dict, urgency: str) -> List[Dict]:
        if not all_slots:
            print("No participant slots provided")
            return []
        
        print(f"Finding common slots among {len(all_slots)} participants")
        
        all_time_slots = set()
        for participant_email, participant_slots in all_slots.items():
            print(f"   {participant_email}: {len(participant_slots)} slots")
            for slot in participant_slots:
                if isinstance(slot, dict) and 'start_time' in slot and 'end_time' in slot:
                    slot_key = (slot['start_time'], slot['end_time'])
                    all_time_slots.add(slot_key)
        
        print(f"Total unique time slots: {len(all_time_slots)}")
        
        common_slots = []
        for start_time, end_time in all_time_slots:
            participants_with_slot = []
            total_preference = 0
            
            for participant_email, participant_slots in all_slots.items():
                found_slot = None
                for slot in participant_slots:
                    if (slot.get('start_time') == start_time and 
                        slot.get('end_time') == end_time):
                        found_slot = slot
                        break
                
                if found_slot:
                    participants_with_slot.append(participant_email)
                    total_preference += found_slot.get('preference_score', 0.5)
            
            if len(participants_with_slot) == len(all_slots):
                avg_preference = total_preference / len(all_slots)
                
                min_threshold = 0.1 if urgency == 'urgent' else 0.2
                
                if avg_preference >= min_threshold:
                    common_slots.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'average_preference': avg_preference
                    })
                    
                    start_dt = datetime.fromisoformat(start_time)
                    print(f"   Common slot: {start_dt.strftime('%H:%M')} - ALL participants available (avg score: {avg_preference:.2f})")
                else:
                    start_dt = datetime.fromisoformat(start_time)
                    print(f"   Low preference: {start_dt.strftime('%H:%M')} - Available but preference too low ({avg_preference:.2f})")
            else:
                start_dt = datetime.fromisoformat(start_time)
                print(f"   Partial availability: {start_dt.strftime('%H:%M')} - Only {len(participants_with_slot)}/{len(all_slots)} participants available")
        
        print(f"Final common slots: {len(common_slots)}")
        return common_slots
    
    async def _calculate_consensus_fast(self, participants: List, slot: Dict, urgency: str) -> float:
        total_score = 0
        valid_count = 0
        
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal(slot, urgency=urgency)
                score = evaluation.get('preference_score', 0)
                
                if urgency == 'urgent' and evaluation['decision'] in ['ACCEPT', 'CONDITIONAL_ACCEPT']:
                    score = max(score, 0.6)
                
                total_score += score
                valid_count += 1
            except Exception as e:
                print(f"Error in consensus calc for {participant.email}: {e}")
                total_score += 0.5
                valid_count += 1
        
        return total_score / valid_count if valid_count > 0 else 0
    
    def _calculate_urgency_bonus(self, slot: Dict, urgency: str) -> float:
        try:
            hour = datetime.fromisoformat(slot['start_time']).hour
            
            if urgency == 'urgent':
                return 0.3 if 7 <= hour <= 20 else 0.1
            elif urgency == 'high':
                return 0.2 if 9 <= hour <= 18 else 0.1
            else:
                return 0.1 if 9 <= hour <= 17 else 0
        except:
            return 0
    
    async def _extended_urgency_negotiation(self, participants: List, target_date: str, 
                                          duration_mins: int, urgency: str, context: str) -> Dict:
        print("Initiating extended urgency negotiation")
        
        extended_options = []
        
        for participant in participants:
            try:
                rescheduling_prompt = f"""
                URGENT MEETING ACCOMMODATION REQUEST
                
                No standard time slots are available for this {urgency} priority meeting on {target_date}.
                
                As {participant.email}, can you:
                1. Reschedule any existing meetings?
                2. Accept a meeting outside normal hours?
                3. Suggest the earliest possible alternative date?
                
                Context: {context}
                
                Respond with: RESCHEDULE_POSSIBLE|ACCEPT_OFF_HOURS|SUGGEST_ALTERNATIVE|CANNOT_ACCOMMODATE
                """
                
                response = await self.llm.generate_async(rescheduling_prompt, max_tokens=50)
                
                if 'RESCHEDULE_POSSIBLE' in response.upper():
                    extended_options.append({
                        'participant': participant.email,
                        'option': 'reschedule_existing',
                        'response': response
                    })
                elif 'ACCEPT_OFF_HOURS' in response.upper():
                    extended_options.append({
                        'participant': participant.email,
                        'option': 'off_hours_acceptance',
                        'response': response
                    })
                    
            except Exception as e:
                print(f"Extended negotiation failed for {participant.email}: {e}")
                continue
        
        if len(extended_options) >= len(participants) * 0.7:
            
            record_negotiator(
                action="achieve extended urgent accommodation",
                outcome=f"found creative solutions with {len(extended_options)} participants",
                reasoning="Urgent priority justified extraordinary scheduling measures"
            )
            
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            
            urgent_time = self.default_timezone.localize(
                target_dt.replace(hour=7, minute=0, second=0, microsecond=0)
            )
            urgent_end = urgent_time + timedelta(minutes=duration_mins)
            
            return {
                'success': True,
                'slot': {
                    'start_time': urgent_time.isoformat(),
                    'end_time': urgent_end.isoformat(),
                    'time_display': self._format_time_display(urgent_time.isoformat())
                },
                'extended_accommodations': extended_options,
                'consensus_score': 0.8,
                'negotiation_type': 'extended_urgent'
            }
        
        return {'success': False, 'reason': 'Extended urgent negotiation could not find viable accommodations'}
    
    async def _negotiate_best_slot_with_urgency(self, participants: List, alternative_slots: List[Dict], 
                                              urgency: str, context: str) -> Dict:
        if not alternative_slots:
            return None
        
        print(f"Selecting best slot from {len(alternative_slots)} options")
        
        best_slot = alternative_slots[0]
        print(f"Selected: {best_slot['time_display']} (score: {best_slot['overall_score']:.2f})")
        
        final_evaluations = []
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal(best_slot, context=context, urgency=urgency)
                final_evaluations.append(evaluation)
                print(f"   {participant.email}: {evaluation['decision']} ({evaluation.get('preference_score', 0):.2f})")
            except Exception as e:
                print(f"Error in final eval for {participant.email}: {e}")
                final_evaluations.append({
                    'decision': 'ACCEPT',
                    'reason': 'default_accept',
                    'preference_score': 0.5,
                    'participant': participant.email
                })
        
        return {
            'success': True,
            'slot': best_slot,
            'evaluations': final_evaluations,
            'consensus_score': best_slot['overall_score'],
            'urgency_level': urgency
        }
    
    def _create_urgency_aware_selection_reasoning(self, best_slot: Dict, all_slots: List[Dict], 
                                                participants: List, urgency: str) -> str:
        selected_time = best_slot['slot']['time_display']
        consensus_score = best_slot['consensus_score']
        
        reasoning_parts = []
        
        if urgency == 'urgent':
            reasoning_parts.append(f"Selected {selected_time} for URGENT priority meeting")
        elif urgency == 'high':
            reasoning_parts.append(f"Selected {selected_time} for HIGH priority meeting")
        else:
            reasoning_parts.append(f"Selected {selected_time} after analyzing {len(all_slots)} possible times")
        
        if consensus_score >= 0.8:
            reasoning_parts.append("achieved excellent participant accommodation")
        elif consensus_score >= 0.6:
            reasoning_parts.append("provided good balance of participant needs")
        else:
            reasoning_parts.append("represents best available compromise given constraints")
        
        hour = datetime.fromisoformat(best_slot['slot']['start_time']).hour
        if 9 <= hour <= 17:
            reasoning_parts.append("scheduled during optimal business hours")
        elif urgency in ['urgent', 'high'] and (7 <= hour <= 20):
            reasoning_parts.append(f"accommodated {urgency} priority with extended hours")
        
        if urgency in ['urgent', 'high']:
            reasoning_parts.append(f"balanced {urgency} business needs with participant availability")
        else:
            reasoning_parts.append(f"ensured all {len(participants)} participants can attend comfortably")
        
        return ". ".join(reasoning_parts).capitalize() + "."
    
    def _build_requested_time(self, parsed_email: Dict, target_date: str, duration_mins: int) -> Dict:
        suggested_time = parsed_email.get('suggested_time')
        if not suggested_time:
            return None
        
        try:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            time_parts = suggested_time.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            
            start_dt = date_obj.replace(hour=hour, minute=minute)
            end_dt = start_dt + timedelta(minutes=duration_mins)
            
            start_dt = self.default_timezone.localize(start_dt)
            end_dt = self.default_timezone.localize(end_dt)
            
            return {
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat()
            }
        except Exception as e:
            print(f"Error building requested time: {e}")
            return None
    
    def _create_success_response(self, result: Dict, meeting_request: Dict, alternatives: List[Dict]) -> Dict:
        slot = result['slot']
        
        return {
            'success': True,
            'scheduled_slot': {
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'display_time': slot['time_display']
            },
            'alternatives_considered': [
                {
                    'start_time': alt['start_time'],
                    'end_time': alt['end_time'],
                    'time_display': alt['time_display']
                } for alt in alternatives[:3]
            ],
            'negotiation_summary': {
                'consensus_score': result['consensus_score'],
                'total_participants': len(result['evaluations']),
                'urgency_level': result.get('urgency_level', 'medium'),
                'negotiation_type': result.get('negotiation_type', 'standard')
            }
        }
    
    def _create_failure_response(self, meeting_request: Dict, reason: str) -> Dict:
        return {
            'success': False,
            'reason': reason,
            'alternatives_considered': [],
            'negotiation_summary': {
                'consensus_score': 0,
                'total_participants': len(meeting_request.get('Attendees', [])),
                'urgency_level': self._extract_urgency_from_email(meeting_request.get('EmailContent', '')),
                'negotiation_type': 'failed'
            }
        }
    
    def _get_default_date(self) -> str:
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    def _format_time_display(self, iso_time: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_time)
            return dt.strftime("%H:%M IST")
        except:
            return iso_time