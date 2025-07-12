import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from services.llm_service import LLMService
from utils.email_parser import EmailParser
import pytz

logger = logging.getLogger(__name__)


class NegotiatorAgent:
    def __init__(self, llm_client: LLMService | None = None) -> None:
        self.llm = llm_client or LLMService()
        self.email_parser = EmailParser(self.llm)
        self.negotiation_history: List[Dict[str, Any]] = []
        self.default_timezone = pytz.timezone("Asia/Kolkata")

    async def negotiate_meeting(
        self, participants: List, meeting_request: Dict
    ) -> Dict:
        duration_mins = int(meeting_request.get("Duration_mins", 30))
        email_content = meeting_request.get("EmailContent", "")
        parsed_email = self.email_parser.parse_email(email_content)
        target_date = parsed_email.get("suggested_date", self._get_default_date())
        requested_time = self._build_requested_time(
            parsed_email, target_date, duration_mins
        )

        logger.info(
            "Negotiating meeting for %d participants (target date %s, duration %d min)",
            len(participants),
            target_date,
            duration_mins,
        )

        if requested_time and requested_time.get("start"):
            logger.debug("Evaluating specifically requested time")
            initial_result = await self._evaluate_specific_time(
                participants, requested_time, duration_mins
            )
            if initial_result["success"]:
                logger.info("Requested time accepted by all participants")
                return self._create_success_response(
                    initial_result, meeting_request, []
                )
            logger.info(
                "Requested time rejected: %d conflict(s)",
                len(initial_result["conflicts"]),
            )

        logger.debug("Searching for alternative slots")
        alternative_slots = await self._find_alternative_slots(
            participants, target_date, duration_mins
        )
        if not alternative_slots:
            logger.warning("No alternative slots found")
            return self._create_failure_response(
                meeting_request, "No available slots found"
            )

        best_slot = await self._negotiate_best_slot(participants, alternative_slots)
        if not best_slot:
            return self._create_failure_response(
                meeting_request, "Could not find acceptable compromise"
            )

        logger.info("Selected best slot: %s", best_slot["slot"]["time_display"])
        return self._create_success_response(
            best_slot, meeting_request, alternative_slots
        )

    def _build_requested_time(
        self, parsed_email: Dict, target_date: str, duration_mins: int
    ) -> Dict | None:
        suggested_time = parsed_email.get("suggested_time")
        if not suggested_time:
            return None
        try:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d")
            hour, *min_part = map(int, suggested_time.split(":"))
            minute = min_part[0] if min_part else 0
            start_dt = date_obj.replace(hour=hour, minute=minute)
            end_dt = start_dt + timedelta(minutes=duration_mins)
            start_dt = self.default_timezone.localize(start_dt)
            end_dt = self.default_timezone.localize(end_dt)
            return {"start": start_dt.isoformat(), "end": end_dt.isoformat()}
        except Exception as exc:
            logger.error("Error building requested time: %s", exc, exc_info=True)
            return None

    async def _evaluate_specific_time(
        self, participants: List, requested_time: Dict, duration_mins: int
    ) -> Dict:
        evaluations, conflicts = [], []
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal(
                    {
                        "start_time": requested_time["start"],
                        "end_time": requested_time["end"],
                    }
                )
                evaluations.append(evaluation)
                if evaluation["decision"] == "REJECT":
                    conflicts.append(
                        {
                            "participant": participant.email,
                            "reason": evaluation["reason"],
                            "timezone": evaluation.get("timezone", "Asia/Kolkata"),
                        }
                    )
            except Exception as exc:
                logger.error(
                    "Evaluation failed for %s: %s", participant.email, exc, exc_info=True
                )
                evaluations.append(
                    {
                        "decision": "REJECT",
                        "reason": "evaluation_failed",
                        "preference_score": 0,
                        "participant": participant.email,
                        "timezone": "Asia/Kolkata",
                    }
                )
                conflicts.append(
                    {
                        "participant": participant.email,
                        "reason": "evaluation_failed",
                        "timezone": "Asia/Kolkata",
                    }
                )

        success = not conflicts
        consensus_score = (
            sum(e.get("preference_score", 0) for e in evaluations) / len(evaluations)
            if evaluations
            else 0
        )
        return {
            "success": success,
            "slot": {
                "start_time": requested_time["start"],
                "end_time": requested_time["end"],
                "time_display": self._format_time_display(requested_time["start"]),
            },
            "evaluations": evaluations,
            "conflicts": conflicts,
            "consensus_score": consensus_score,
        }

    async def _find_alternative_slots(
        self, participants: List, target_date: str, duration_mins: int
    ) -> List[Dict]:
        all_available_slots: Dict[str, List[Dict]] = {}
        for participant in participants:
            try:
                slots = participant.find_available_slots(target_date, duration_mins)
                all_available_slots[participant.email] = slots
                logger.debug("%s: %d slot(s)", participant.email, len(slots))
            except Exception as exc:
                logger.error("Slot search failed for %s: %s", participant.email, exc)
                all_available_slots[participant.email] = []

        common_slots = self._find_common_time_slots(all_available_slots, duration_mins)
        logger.debug("%d common slot(s) found", len(common_slots))

        scored_slots = []
        for slot in common_slots:
            try:
                consensus_score = await self._calculate_consensus_score(
                    participants, slot
                )
                timezone_fairness = self._calculate_timezone_fairness(
                    participants, slot
                )
                scored_slots.append(
                    {
                        "start_time": slot["start_time"],
                        "end_time": slot["end_time"],
                        "consensus_score": consensus_score,
                        "timezone_fairness": timezone_fairness,
                        "overall_score": consensus_score * 0.7
                        + timezone_fairness * 0.3,
                        "time_display": self._format_time_display(slot["start_time"]),
                    }
                )
            except Exception as exc:
                logger.error("Scoring slot failed: %s", exc, exc_info=True)

        return sorted(scored_slots, key=lambda x: x["overall_score"], reverse=True)[:10]

    def _find_common_time_slots(
        self, all_slots: Dict[str, List[Dict]], duration_mins: int
    ) -> List[Dict]:
        if not all_slots:
            return []
        unique = {
            (slot["start_time"], slot["end_time"])
            for slots in all_slots.values()
            for slot in slots
        }
        common = []
        for start, end in unique:
            if all(
                any(
                    s["start_time"] == start and s["end_time"] == end
                    for s in slots
                )
                for slots in all_slots.values()
            ):
                common.append({"start_time": start, "end_time": end})
        return common

    async def _calculate_consensus_score(
        self, participants: List, slot: Dict
    ) -> float:
        total, count = 0.0, 0
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal(slot)
                total += evaluation.get("preference_score", 0)
                count += 1
            except Exception as exc:
                logger.error(
                    "Consensus score eval failed for %s: %s",
                    participant.email,
                    exc,
                    exc_info=True,
                )
        return total / count if count else 0.0

    def _calculate_timezone_fairness(
        self, participants: List, slot: Dict
    ) -> float:
        try:
            start_time = datetime.fromisoformat(slot["start_time"])
            scores = []
            for participant in participants:
                try:
                    tz = getattr(participant, "timezone", self.default_timezone)
                    if isinstance(tz, str):
                        tz = pytz.timezone(tz)
                    local_time = start_time.astimezone(tz)
                    hour = local_time.hour
                    if 9 <= hour <= 17:
                        scores.append(1.0)
                    elif 8 <= hour <= 18:
                        scores.append(0.8)
                    elif 7 <= hour <= 19:
                        scores.append(0.6)
                    else:
                        scores.append(0.2)
                except Exception as exc:
                    logger.error(
                        "Timezone fairness calc failed for %s: %s",
                        participant.email,
                        exc,
                        exc_info=True,
                    )
                    scores.append(0.5)
            return sum(scores) / len(scores) if scores else 0.5
        except Exception as exc:
            logger.error("Timezone fairness error: %s", exc, exc_info=True)
            return 0.5

    async def _negotiate_best_slot(
        self, participants: List, alternative_slots: List[Dict]
    ) -> Dict | None:
        if not alternative_slots:
            return None
        try:
            prompt = await self._build_negotiation_prompt(
                participants, alternative_slots
            )
            llm_response = await self.llm.generate_async(prompt, max_tokens=200)
            selected_index = self._parse_llm_selection(
                llm_response, len(alternative_slots)
            )
        except Exception as exc:
            logger.error("LLM negotiation failed: %s", exc, exc_info=True)
            llm_response = "Fallback to highest scored option"
            selected_index = 0

        best_slot = alternative_slots[selected_index]
        evaluations = []
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal(best_slot)
                evaluations.append(evaluation)
            except Exception as exc:
                logger.error(
                    "Final evaluation failed for %s: %s",
                    participant.email,
                    exc,
                    exc_info=True,
                )
                evaluations.append(
                    {
                        "decision": "ACCEPT",
                        "reason": "default_accept",
                        "preference_score": 0.5,
                        "participant": participant.email,
                        "timezone": "Asia/Kolkata",
                    }
                )
        return {
            "success": True,
            "slot": best_slot,
            "evaluations": evaluations,
            "conflicts": [],
            "consensus_score": best_slot["overall_score"],
            "selection_reasoning": llm_response,
        }

    async def _build_negotiation_prompt(
        self, participants: List, alternatives: List[Dict]
    ) -> str:
        participant_lines = []
        for p in participants:
            try:
                tz_name = getattr(p, "timezone", self.default_timezone)
                if hasattr(tz_name, "zone"):
                    tz_name = tz_name.zone
                participant_lines.append(
                    f"- {p.email}: timezone {tz_name}, preferences {getattr(p, 'preferences', {})}"
                )
            except Exception:
                participant_lines.append(f"- {p.email}: timezone Asia/Kolkata")

        alt_lines = [
            f"{i}: {alt['time_display']} (score: {alt['overall_score']:.2f})"
            for i, alt in enumerate(alternatives[:5])
        ]
        return (
            "You are an AI meeting negotiator. Choose the best meeting option.\n\n"
            "Participants:\n"
            + "\n".join(participant_lines)
            + "\n\nAvailable options:\n"
            + "\n".join(alt_lines)
            + f"\n\nRespond only with the number 0-{min(4, len(alternatives)-1)}."
        )

    def _parse_llm_selection(self, llm_response: str, max_options: int) -> int:
        import re

        matches = re.findall(r"\b(\d+)\b", llm_response)
        if matches:
            return min(int(matches[0]), max_options - 1)
        return 0

    def _create_success_response(
        self, result: Dict, meeting_request: Dict, alternatives: List[Dict]
    ) -> Dict:
        slot = result["slot"]
        return {
            "success": True,
            "scheduled_slot": {
                "start_time": slot["start_time"],
                "end_time": slot["end_time"],
                "display_time": slot["time_display"],
            },
            "alternatives_considered": [
                {
                    "start_time": alt["start_time"],
                    "end_time": alt["end_time"],
                    "overall_score": alt["overall_score"],
                    "time_display": alt["time_display"],
                }
                for alt in alternatives[:5]
            ],
            "negotiation_summary": {
                "consensus_score": result["consensus_score"],
                "conflicts_resolved": sum(
                    e["decision"] == "ACCEPT" for e in result["evaluations"]
                ),
                "total_participants": len(result["evaluations"]),
                "selection_reasoning": result.get(
                    "selection_reasoning", "Optimal consensus achieved"
                ),
            },
        }

    def _create_failure_response(self, meeting_request: Dict, reason: str) -> Dict:
        return {
            "success": False,
            "reason": reason,
            "alternatives_considered": [],
            "negotiation_summary": {
                "consensus_score": 0,
                "conflicts_resolved": 0,
                "total_participants": len(meeting_request.get("Attendees", [])),
                "selection_reasoning": f"Failed: {reason}",
            },
        }

    def _get_default_date(self) -> str:
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    def _format_time_display(self, iso_time: str) -> str:
        try:
            return datetime.fromisoformat(iso_time).strftime("%H:%M IST")
        except ValueError:
            return iso_time
