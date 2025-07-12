import re
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class JSONValidator:
    _EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_request(self, data: Dict) -> Dict[str, Any]:
        self._reset()
        if not isinstance(data, dict):
            self.errors.append('Request must be a valid JSON object')
            return self._result()
        required = [
            'Request_id', 'Datetime', 'Location', 'From',
            'Attendees', 'Subject', 'EmailContent'
        ]
        self._check_required_fields(data, required)
        self._check_field_types(data)
        self._check_attendees_input(data)
        self._check_datetime_fields(data, ['Datetime', 'EventStart', 'EventEnd'])
        return self._result()

    def validate_response(self, data: Dict) -> Dict[str, Any]:
        self._reset()
        required = [
            'Request_id', 'Datetime', 'Location', 'From', 'Attendees',
            'Subject', 'EmailContent', 'EventStart', 'EventEnd',
            'Duration_mins', 'MetaData'
        ]
        self._check_required_fields(data, required)
        if 'EventStart' in data:
            self._validate_datetime('EventStart', data['EventStart'])
        if 'EventEnd' in data:
            self._validate_datetime('EventEnd', data['EventEnd'])
        if 'Attendees' in data:
            self._check_attendees_output(data['Attendees'])
        return self._result()

    @staticmethod
    def sanitize_request(data: Dict) -> Dict:
        cleaned = data.copy()
        for key in ('EmailContent', 'Subject', 'From', 'Location'):
            if isinstance(cleaned.get(key), str):
                cleaned[key] = cleaned[key].strip()
        cleaned.setdefault('Request_id', f"req_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        for attendee in cleaned.get('Attendees', []):
            if isinstance(attendee, dict) and 'email' in attendee:
                attendee['email'] = attendee['email'].strip().lower()
        logger.debug('Sanitized request payload: %s', cleaned)
        return cleaned

    def _reset(self) -> None:
        self.errors = []
        self.warnings = []

    def _result(self) -> Dict[str, Any]:
        valid = not self.errors
        if valid:
            logger.info('Validation succeeded')
        else:
            logger.warning('Validation failed: %s', self.errors)
        return {
            'valid': valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }

    def _check_required_fields(self, data: Dict, fields: List[str]) -> None:
        for field in fields:
            if field not in data:
                self.errors.append(f'Missing required field: {field}')
            elif data[field] in (None, ''):
                self.errors.append(f'Required field cannot be empty: {field}')

    def _check_field_types(self, data: Dict) -> None:
        if 'EmailContent' in data and not isinstance(data['EmailContent'], str):
            self.errors.append('EmailContent must be a string')
        if 'Attendees' in data and not isinstance(data['Attendees'], list):
            self.errors.append('Attendees must be a list')
        if 'From' in data and data['From'] and not self._EMAIL_RE.match(data['From']):
            self.errors.append('From field must be a valid email')

    def _check_attendees_input(self, data: Dict) -> None:
        attendees = data.get('Attendees', [])
        if not attendees:
            self.errors.append('At least one attendee is required')
            return
        for idx, att in enumerate(attendees):
            if not isinstance(att, dict):
                self.errors.append(f'Attendee {idx} must be an object')
                continue
            email = att.get('email')
            if not email:
                self.errors.append(f'Attendee {idx} missing email field')
            elif not self._EMAIL_RE.match(email):
                self.errors.append(f'Attendee {idx} has invalid email format')

    def _check_attendees_output(self, attendees: List[Dict]) -> None:
        for i, att in enumerate(attendees):
            if not isinstance(att, dict):
                self.errors.append(f'Output attendee {i} must be an object')
                continue
            if 'email' not in att:
                self.errors.append(f'Output attendee {i} missing email field')
            if 'events' not in att:
                self.errors.append(f'Output attendee {i} missing events field')
                continue
            if isinstance(att['events'], list):
                self._check_attendee_events(att['events'], i)

    def _check_attendee_events(self, events: List[Dict], idx: int) -> None:
        required = ['StartTime', 'EndTime', 'Summary', 'Attendees', 'NumAttendees']
        for j, ev in enumerate(events):
            if not isinstance(ev, dict):
                self.errors.append(f'Attendee {idx} event {j} must be an object')
                continue
            for field in required:
                if field not in ev:
                    self.errors.append(f'Attendee {idx} event {j} missing {field}')
            if 'StartTime' in ev:
                self._validate_datetime(f'Attendee {idx} event {j} StartTime', ev['StartTime'])
            if 'EndTime' in ev:
                self._validate_datetime(f'Attendee {idx} event {j} EndTime', ev['EndTime'])
            try:
                start = datetime.fromisoformat(ev['StartTime'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(ev['EndTime'].replace('Z', '+00:00'))
                if end <= start:
                    self.errors.append(f'Attendee {idx} event {j} end time must be after start time')
            except Exception:
                pass

    def _check_datetime_fields(self, data: Dict, fields: List[str]) -> None:
        for field in fields:
            if field in data and data[field]:
                self._validate_datetime(field, data[field])

    def _validate_datetime(self, label: str, dt_string: str) -> None:
        if not self._is_valid_datetime(dt_string):
            self.errors.append(f'Invalid datetime format for {label}')

    @staticmethod
    def _is_valid_datetime(dt_str: str) -> bool:
        try:
            if dt_str.endswith('Z'):
                dt_str = dt_str.replace('Z', '+00:00')
            datetime.fromisoformat(dt_str)
            return True
        except (ValueError, TypeError):
            try:
                datetime.strptime(dt_str, '%d-%m-%YT%H:%M:%S')
                return True
            except (ValueError, TypeError):
                return False


def validate_json_request(data: Dict) -> Dict[str, Any]:
    return JSONValidator().validate_request(data)


def validate_json_response(data: Dict) -> Dict[str, Any]:
    return JSONValidator().validate_response(data)


def clean_json_request(data: Dict) -> Dict:
    return JSONValidator().sanitize_request(data)
