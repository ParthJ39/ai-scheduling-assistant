import os
from typing import Dict, Any

LLM_CONFIG = {
    'base_url': os.getenv('VLLM_BASE_URL', 'http://localhost:3000/v1'),
    'model_name': os.getenv('LLM_MODEL', '/home/user/Models/deepseek-ai/deepseek-llm-7b-chat'),
    'timeout': int(os.getenv('LLM_TIMEOUT', '30')),
    'max_retries': int(os.getenv('LLM_MAX_RETRIES', '3')),
    
    'openai_api_key': os.getenv('OPENAI_API_KEY'),
    'openai_model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
    
    'temperature': float(os.getenv('LLM_TEMPERATURE', '0.7')),
    'max_tokens': int(os.getenv('LLM_MAX_TOKENS', '512')),
    'top_p': float(os.getenv('LLM_TOP_P', '0.9')),
}

CALENDAR_CONFIG = {
    'default_timezone': os.getenv('DEFAULT_TIMEZONE', 'Asia/Kolkata'),
    'business_start_hour': int(os.getenv('BUSINESS_START_HOUR', '9')),
    'business_end_hour': int(os.getenv('BUSINESS_END_HOUR', '18')),
    'working_days': [0, 1, 2, 3, 4],
    'slot_duration_minutes': int(os.getenv('SLOT_DURATION_MINUTES', '15')),
    'buffer_minutes': int(os.getenv('DEFAULT_BUFFER_MINUTES', '15')),
}

AGENT_CONFIG = {
    'max_negotiation_rounds': int(os.getenv('MAX_NEGOTIATION_ROUNDS', '3')),
    'consensus_threshold': float(os.getenv('CONSENSUS_THRESHOLD', '0.6')),
    'preference_weight': float(os.getenv('PREFERENCE_WEIGHT', '0.7')),
    'timezone_fairness_weight': float(os.getenv('TIMEZONE_FAIRNESS_WEIGHT', '0.3')),
    'default_meeting_duration': int(os.getenv('DEFAULT_MEETING_DURATION', '30')),
}

API_CONFIG = {
    'host': os.getenv('API_HOST', '0.0.0.0'),
    'port': int(os.getenv('API_PORT', '5000')),
    'debug': os.getenv('API_DEBUG', 'True').lower() == 'true',
    'cors_enabled': os.getenv('CORS_ENABLED', 'True').lower() == 'true',
}

LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    'file_path': os.getenv('LOG_FILE_PATH', 'scheduler.log'),
    'max_file_size': int(os.getenv('LOG_MAX_FILE_SIZE', '10485760')),
    'backup_count': int(os.getenv('LOG_BACKUP_COUNT', '5')),
}

GPU_CONFIG = {
    'enabled': os.getenv('GPU_ENABLED', 'False').lower() == 'true',
    'device_id': int(os.getenv('GPU_DEVICE_ID', '0')),
    'memory_fraction': float(os.getenv('GPU_MEMORY_FRACTION', '0.85')),
    'parallel_agents': int(os.getenv('GPU_PARALLEL_AGENTS', '6')),
    'batch_size': int(os.getenv('GPU_BATCH_SIZE', '32')),
}

TIMEZONE_MAPPING = {
    'gmail.com': 'America/New_York',
    'outlook.com': 'America/New_York', 
    'company.com': 'America/New_York',
    'microsoft.com': 'America/Los_Angeles',
    'google.com': 'America/Los_Angeles',
    'apple.com': 'America/Los_Angeles',
    'amazon.com': 'America/Los_Angeles',
    'bbc.co.uk': 'Europe/London',
    'reuters.com': 'Europe/London',
    'hsbc.com': 'Europe/London',
    'barclays.com': 'Europe/London',
    'amd.com': 'Asia/Kolkata',
    'infosys.com': 'Asia/Kolkata',
    'tcs.com': 'Asia/Kolkata',
    'wipro.com': 'Asia/Kolkata',
    'sony.co.jp': 'Asia/Tokyo',
    'toyota.com': 'Asia/Tokyo',
    'samsung.com': 'Asia/Seoul'
}

TEST_SCENARIOS = {
    "easy": {
        "participants": ["user1@company.com", "user2@gmail.com"],
        "calendar_complexity": "normal",
        "description": "2 participants with minimal conflicts"
    },
    "medium": {
        "participants": ["user1@company.com", "user2@gmail.com", "user3@bbc.co.uk"],
        "calendar_complexity": "normal", 
        "description": "3 participants across timezones with some conflicts"
    },
    "hard": {
        "participants": ["user1@company.com", "user2@gmail.com", "user3@bbc.co.uk", "user4@amd.com"],
        "calendar_complexity": "heavy_conflict",
        "description": "4 participants across timezones with heavy conflicts"
    },
    "urgent_hard": {
        "participants": ["user1@company.com", "user2@gmail.com", "user3@bbc.co.uk", "user4@amd.com", "user5@sony.co.jp"],
        "calendar_complexity": "heavy_conflict",
        "urgency_keywords": ["urgent", "asap", "emergency", "critical"],
        "description": "5 participants across timezones with heavy conflicts and urgency"
    }
}

VALIDATION_RULES = {
    'min_meeting_duration': 15,
    'max_meeting_duration': 480,
    'max_attendees': 20,
    'max_date_range_days': 30,
    'required_fields': ['EmailContent', 'Attendees'],
}

DEFAULT_USER_PREFERENCES = {
    'preferred_times': ['morning', 'afternoon'],
    'buffer_minutes': 15,
    'max_meeting_length': 120,
    'avoid_lunch': True,
    'seniority_weight': 0.5,
    'avoid_back_to_back': True,
    'focus_time_blocks': False,
}

def get_timezone_for_email(email: str) -> str:
    domain = email.split('@')[-1].lower()
    return TIMEZONE_MAPPING.get(domain, 'Asia/Kolkata')

def get_user_preferences(email: str) -> Dict:
    timezone = get_timezone_for_email(email)
    
    preferences = DEFAULT_USER_PREFERENCES.copy()
    preferences['timezone'] = timezone
    
    if 'europe' in timezone.lower():
        preferences['preferred_times'] = ['morning', 'afternoon']
        preferences['avoid_lunch'] = True
    elif 'america' in timezone.lower():
        preferences['preferred_times'] = ['morning', 'afternoon'] 
        preferences['buffer_minutes'] = 10
    elif 'asia' in timezone.lower():
        preferences['preferred_times'] = ['morning']
        preferences['buffer_minutes'] = 15
    
    return preferences

def get_config() -> Dict[str, Any]:
    return {
        'llm': LLM_CONFIG,
        'calendar': CALENDAR_CONFIG,
        'agent': AGENT_CONFIG,
        'api': API_CONFIG,
        'logging': LOGGING_CONFIG,
        'gpu': GPU_CONFIG,
        'validation': VALIDATION_RULES,
        'default_preferences': DEFAULT_USER_PREFERENCES,
        'test_scenarios': TEST_SCENARIOS,
    }

def validate_config() -> bool:
    errors = []
    
    if not LLM_CONFIG['base_url']:
        errors.append("LLM base URL not configured")
    
    try:
        import pytz
        pytz.timezone(CALENDAR_CONFIG['default_timezone'])
    except:
        errors.append(f"Invalid timezone: {CALENDAR_CONFIG['default_timezone']}")
    
    if CALENDAR_CONFIG['business_start_hour'] >= CALENDAR_CONFIG['business_end_hour']:
        errors.append("Invalid business hours configuration")
    
    if errors:
        print("Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True