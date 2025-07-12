import pytz
import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta
from resources.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ParticipantAgent:
    def __init__(
        self,
        email: str,
        calendar_data: List[Dict[str, Any]],
        preferences: Dict[str, Any],
        llm_client: LLMService | None = None,
    ):
        self.email = email
        self.calendar = calendar_data
        self.preferences = preferences
        self.llm = llm_client or LLMService()
        self.timezone = pytz.timezone(preferences.get("timezone", "Asia/Kolkata"))

    def find_available_slots(
        self, date_str: str, duration_mins: int, time_window_hours: int = 10
    ) -> List[Dict[str, Any]]:
        available: List[Dict[str, Any]] = []
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = self.timezone.localize(
            datetime.combine(target_date, datetime.min.time().replace(hour=9))
        )
        end = self.timezone.localize(
            datetime.combine(target_date, datetime.min.time().replace(hour=18))
        )

        cur = start
        while cur + timedelta(minutes=duration_mins) <= end:
            slot_end = cur + timedelta(minutes=duration_mins)
            if not self._has_conflict(cur, slot_end):
                score = self._calculate_preference_score(cur)
                available.append(
                    {
                        "start_time": cur.isoformat(),
                        "end_time": slot_end.isoformat(),
                        "preference_score": score,
                        "participant": self.email,
                    }
                )
            cur += timedelta(minutes=15)

        return sorted(available, key=lambda x: x["preference_score"], reverse=True)

    def _has_conflict(self, start_time: datetime, end_time: datetime) -> bool:
        for event in self.calendar:
            ev_start = datetime.fromisoformat(event["StartTime"].replace("Z", "+00:00"))
            ev_end = datetime.fromisoformat(event["EndTime"].replace("Z", "+00:00"))
            if ev_start.tzinfo != start_time.tzinfo:
                ev_start = ev_start.astimezone(start_time.tzinfo)
                ev_end = ev_end.astimezone(start_time.tzinfo)

            buffer_mins = self.preferences.get("buffer_minutes", 15)
            buffered_start = start_time - timedelta(minutes=buffer_mins)
            buffered_end = end_time + timedelta(minutes=buffer_mins)
            if not (buffered_end <= ev_start or buffered_start >= ev_end):
                return True
        return False

    def _calculate_preference_score(self, start_time: datetime) -> float:
        score = 0.5
        hour = start_time.hour
        prefs = self.preferences.get("preferred_times", [])
        if "morning" in prefs and 9 <= hour < 12:
            score += 0.3
        elif "afternoon" in prefs and 13 <= hour < 17:
            score += 0.3
        elif "evening" in prefs and 17 <= hour < 20:
            score += 0.2
        if self.preferences.get("avoid_lunch", False) and 12 <= hour < 14:
            score -= 0.4
        seniority = self.preferences.get("seniority_weight", 0.5)
        return max(0, min(1, score * (0.7 + 0.6 * seniority)))

    async def evaluate_proposal(self, proposed_slot: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        start = datetime.fromisoformat(proposed_slot["start_time"])
        end = datetime.fromisoformat(proposed_slot["end_time"])

        if self._has_conflict(start, end):
            return {
                "decision": "REJECT",
                "reason": "schedule_conflict",
                "preference_score": 0,
                "alternative_suggestions": await self._suggest_alternatives(
                    start.date(), (end - start).total_seconds() / 60
                ),
            }

        preference_score = self._calculate_preference_score(start)
        llm_reasoning = await self._evaluate_with_llm(proposed_slot, preference_score)

        if preference_score >= 0.6:
            decision, reason = "ACCEPT", "good_time_match"
        elif preference_score >= 0.3:
            decision, reason = "CONDITIONAL_ACCEPT", "acceptable_but_not_ideal"
        else:
            decision, reason = "REJECT", "poor_time_preference"

        return {
            "decision": decision,
            "reason": reason,
            "preference_score": preference_score,
            "participant": self.email,
            "timezone": str(self.timezone),
            "llm_reasoning": llm_reasoning,
        }

    async def _evaluate_with_llm(self, proposed_slot: Dict[str, Any], preference_score: float) -> str:
        start_time = datetime.fromisoformat(proposed_slot["start_time"])
        prompt = (
            f"You are {self.email}'s scheduling assistant. Evaluate this meeting proposal:\n\n"
            f"Proposed Time: {start_time.strftime('%A, %B %d at %I:%M %p %Z')}\n"
            f"Preference Score: {preference_score:.2f} (0=poor, 1=excellent)\n"
            f"My Preferences: {self.preferences}\n\n"
            "Provide a brief, professional response explaining whether this time works well. "
            "Keep it under 50 words."
        )
        try:
            response = await self.llm.generate_async(prompt, max_tokens=100)
            return response.strip()
        except Exception as exc:
            logger.error("LLM evaluation failed for %s: %s", self.email, exc)
            return f"Time preference score: {preference_score:.2f}"

    async def _suggest_alternatives(self, target_date: datetime.date, duration_mins: int) -> List[Dict[str, Any]]:
        available = self.find_available_slots(target_date.strftime("%Y-%m-%d"), duration_mins)
        alternatives: List[Dict[str, Any]] = []
        for slot in available[:3]:
            start_dt = datetime.fromisoformat(slot["start_time"])
            end_dt = datetime.fromisoformat(slot["end_time"])
            reasoning = await self._generate_alternative_reasoning(start_dt)
            alternatives.append(
                {
                    "start_time": slot["start_time"],
                    "end_time": slot["end_time"],
                    "preference_score": slot["preference_score"],
                    "time_display": f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} {start_dt.tzname()}",
                    "reasoning": reasoning,
                }
            )
        return alternatives

    async def _generate_alternative_reasoning(self, start_time: datetime) -> str:
        prompt = (
            f"Briefly explain why {start_time.strftime('%I:%M %p')} on "
            f"{start_time.strftime('%A')} would be a good alternative meeting time "
            f"for someone with these preferences: {self.preferences}\n\n"
            "Keep it under 30 words and be specific about timing benefits."
        )
        try:
            response = await self.llm.generate_async(prompt, max_tokens=60)
            return response.strip()
        except Exception as exc:
            logger.warning("Alternative reasoning generation failed: %s", exc)
            hour = start_time.hour
            if 9 <= hour < 12:
                return "Morning slot – good for focus"
            if 13 <= hour < 17:
                return "Afternoon slot – collaborative window"
            return "Fits current availability"

