#!/usr/bin/env python3
"""
Test script to verify the correct "next Thursday" calculation logic
"""

from datetime import datetime, timedelta

def extract_target_date_from_email_fixed(email_content: str, email_datetime: str = None):
    """Fixed version of target date extraction"""
    
    # Use email datetime if provided, otherwise use current time
    if email_datetime:
        try:
            if 'T' in email_datetime:
                date_part = email_datetime.split('T')[0]
                # Handle both DD-MM-YYYY and YYYY-MM-DD formats
                if '-' in date_part:
                    parts = date_part.split('-')
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        reference_date = datetime.strptime(date_part, '%Y-%m-%d')
                    else:  # DD-MM-YYYY
                        reference_date = datetime.strptime(date_part, '%d-%m-%Y')
                else:
                    reference_date = datetime.now()
            else:
                reference_date = datetime.now()
        except:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()
    
    print(f"Reference date: {reference_date.strftime('%Y-%m-%d (%A)')}")
    
    content_lower = email_content.lower()
    
    # Handle "next [weekday]" - should be the very next occurrence
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for i, day in enumerate(weekdays):
        if f'next {day}' in content_lower:
            current_weekday = reference_date.weekday()  # 0=Monday, 6=Sunday
            target_weekday = i  # 0=Monday, 6=Sunday
            
            # Calculate days until next occurrence of this weekday
            if target_weekday > current_weekday:
                days_ahead = target_weekday - current_weekday
            else:
                days_ahead = 7 - current_weekday + target_weekday
            
            target_date = reference_date + timedelta(days=days_ahead)
            
            print(f"Parsed 'next {day}':")
            print(f"  Current weekday: {current_weekday} ({reference_date.strftime('%A')})")
            print(f"  Target weekday: {target_weekday} ({day.title()})")
            print(f"  Days ahead: {days_ahead}")
            print(f"  Result: {target_date.strftime('%Y-%m-%d (%A)')}")
            
            return target_date.strftime('%Y-%m-%d')
    
    return None

# Test cases
test_cases = [
    {
        'email_date': '02-07-2025T12:34:55',  # Wednesday, July 2nd
        'email_content': 'Hi Team. Lets meet next Thursday and discuss about our Goals.',
        'expected': '2025-07-03'  # Thursday, July 3rd (CORRECT)
    },
    {
        'email_date': '09-07-2025T12:34:55',  # Wednesday, July 9th 
        'email_content': 'Hi Team. Lets meet next Thursday and discuss about our Goals.',
        'expected': '2025-07-10'  # Thursday, July 10th (CORRECT)
    },
    {
        'email_date': '10-07-2025T12:34:55',  # Thursday, July 10th
        'email_content': 'Hi Team. Lets meet next Thursday and discuss about our Goals.',
        'expected': '2025-07-17'  # Thursday, July 17th (next week)
    },
    {
        'email_date': '05-07-2025T12:34:55',  # Saturday, July 5th
        'email_content': 'Hi Team. Lets meet next Monday and discuss about our Goals.',
        'expected': '2025-07-07'  # Monday, July 7th
    }
]

print("Testing Fixed Date Logic")
print("=" * 50)

for i, test_case in enumerate(test_cases, 1):
    print(f"\nTest Case {i}:")
    print(f"Email Date: {test_case['email_date']}")
    print(f"Email Content: {test_case['email_content']}")
    print(f"Expected Result: {test_case['expected']}")
    
    result = extract_target_date_from_email_fixed(
        test_case['email_content'], 
        test_case['email_date']
    )
    
    print(f"Actual Result: {result}")
    print(f"✅ CORRECT" if result == test_case['expected'] else "❌ WRONG")
    print("-" * 30)

print("\nSUMMARY:")
print("The fixed logic correctly calculates 'next Thursday' as:")
print("- July 2nd (Wed) → July 3rd (Thu) ✅")
print("- July 9th (Wed) → July 10th (Thu) ✅") 
print("- NOT July 24th as the old system did ❌")