# Mock calendar data and user preferences

USER_PREFERENCES = {
    "userthree.amd@gmail.com": {
        "preferred_times": ["morning"],
        "buffer_minutes": 15,
        "timezone": "Asia/Kolkata",
        "max_meeting_length": 60,
        "avoid_lunch": True,
        "seniority_weight": 0.7
    },
    "userone.amd@gmail.com": {
        "preferred_times": ["morning", "afternoon"],
        "buffer_minutes": 10,
        "timezone": "Asia/Kolkata",
        "max_meeting_length": 90,
        "avoid_lunch": True,
        "seniority_weight": 0.6
    },
    "usertwo.amd@gmail.com": {
        "preferred_times": ["afternoon"],
        "buffer_minutes": 20,
        "timezone": "Asia/Kolkata",
        "max_meeting_length": 75,
        "avoid_lunch": False,
        "seniority_weight": 0.5
    }
}

# Test scenarios for demo
TEST_SCENARIOS = {
    "scenario_1_all_available": {
        "Request_id": "demo_001",
        "EmailContent": "Hi team, let's meet next Thursday for 30 minutes to discuss project updates",
        "Attendees": [
            {
                "email": "usertwo.amd@gmail.com",
                "events": [
                    {
                        "StartTime": "2025-07-17T14:00:00+05:30",
                        "EndTime": "2025-07-17T15:00:00+05:30",
                        "Summary": "Client Call"
                    }
                ]
            },
            {
                "email": "userthree.amd@gmail.com",
                "events": [
                    {
                        "StartTime": "2025-07-17T13:00:00+05:30",
                        "EndTime": "2025-07-17T14:00:00+05:30",
                        "Summary": "Lunch Meeting"
                    }
                ]
            }
        ],
        "Duration_mins": "30",
        "Subject": "Project Updates",
        "From": "usertwo.amd@gmail.com",
        "Location": "Conference Room A"
    },
    
    "scenario_2_partial_conflict": {
        "Request_id": "demo_002",
        "EmailContent": "Urgent client feedback discussion Monday 9 AM",
        "Attendees": [
            {
                "email": "userone.amd@gmail.com",
                "events": [
                    {
                        "StartTime": "2025-07-17T09:00:00+05:30",
                        "EndTime": "2025-07-17T10:00:00+05:30",
                        "Summary": "Team Standup"
                    }
                ]
            },
            {
                "email": "usertwo.amd@gmail.com",
                "events": [
                    {
                        "StartTime": "2025-07-17T14:00:00+05:30",
                        "EndTime": "2025-07-17T15:00:00+05:30",
                        "Summary": "Client Call"
                    }
                ]
            }
        ],
        "Duration_mins": "60",
        "Subject": "Client Feedback",
        "From": "userone.amd@gmail.com",
        "Location": "War Room"
    },
    
    "scenario_3_complex_conflict": {
        "Request_id": "demo_003",
        "EmailContent": "All-hands Tuesday 11 AM for quarterly review",
        "Attendees": [
            {
                "email": "userthree.amd@gmail.com",
                "events": [
                    {
                        "StartTime": "2025-07-17T10:00:00+05:30",
                        "EndTime": "2025-07-17T12:00:00+05:30",
                        "Summary": "Design Workshop"
                    },
                    {
                        "StartTime": "2025-07-17T13:00:00+05:30",
                        "EndTime": "2025-07-17T14:00:00+05:30",
                        "Summary": "Lunch with Customers"
                    }
                ]
            },
            {
                "email": "userone.amd@gmail.com",
                "events": [
                    {
                        "StartTime": "2025-07-17T11:00:00+05:30",
                        "EndTime": "2025-07-17T12:30:00+05:30",
                        "Summary": "Architecture Review"
                    }
                ]
            },
            {
                "email": "usertwo.amd@gmail.com",
                "events": [
                    {
                        "StartTime": "2025-07-17T09:00:00+05:30",
                        "EndTime": "2025-07-17T10:00:00+05:30",
                        "Summary": "Daily Sync"
                    },
                    {
                        "StartTime": "2025-07-17T14:00:00+05:30",
                        "EndTime": "2025-07-17T15:00:00+05:30",
                        "Summary": "Client Call"
                    }
                ]
            }
        ],
        "Duration_mins": "90",
        "Subject": "Quarterly Review",
        "From": "userthree.amd@gmail.com",
        "Location": "Main Conference Room"
    }
}