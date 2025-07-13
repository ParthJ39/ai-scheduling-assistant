# AMD MI300 GPU HACKATHON PROJECT
**Agentic AI Meeting Scheduler**

An intelligent meeting coordination system that autonomously schedules meetings, resolves conflicts, and optimizes calendars using AI-powered decision making.

## 🚀 Problem Statement

Today's meeting coordination is bogged down by time-consuming back-and-forth, manual conflict resolution, and inefficient calendar use challenges. 
Our AI assistant solves this by autonomously scheduling meetings, rescheduling conflicts, and optimizing calendars for maximum efficiency.

## 📋 Problem Description

Current meeting scheduling involves:
- Parsing wide variety of free-form requests
- Juggling conflicting calendars and back-and-forth negotiations
- Suboptimal slot choices and manual conflict resolution
- Valuable time wasted on coordination rather than collaboration

Our AI assistant removes this burden by:
- Understanding natural-language scheduling requests
- Autonomously finding optimal meeting times
- Resolving conflicts automatically
- Continuously optimizing calendars for team efficiency

## 🛠️ Setup Instructions

### 1. Clone Repository & Setup Virtual Environment

```bash
git clone https://github.com/your-org/agentic-ai-scheduler.git
cd agentic-ai-scheduler
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Extracting Google Calendar Events - with Google Auth Tokens to pull Google Calendar Events.
```bash
1. Load user credentials from a token file.
2. Fetch events between specified start/end dates using the Google Calendar API.
````

### 3. Start the vLLM Server
vLLM is a high-performance inference engine that delivers up to 24x higher throughput than standard HuggingFace implementations through advanced memory management and continuous batching. Its PagedAttention algorithm dramatically reduces memory fragmentation, enabling efficient serving of large language models with minimal latency—perfect for real-time scheduling requests.

```bash
vllm serve \
  --model $MODEL_NAME \
  --host $VLLM_HOST \
  --port $VLLM_PORT
```

### 4. Run the Flask Application

```bash
python app.py
```

## 🔧 API Usage

### Schedule Meeting Endpoint

**POST** `/schedule`

**Request Format:**
```json
{
  "Request_id": "6118b54f-907b-4451-8d48-dd13d76033a5",
  "Datetime": "02-07-2025T12:34:55",
  "Location": "IIT Mumbai",
  "From": "userone.amd@gmail.com",
  "Attendees": [
    { "email": "usertwo.amd@gmail.com" },
    { "email": "userthree.amd@gmail.com" }
  ],
  "EmailContent": "Hi Team. Let's meet next Thursday and discuss about our Goals."
}
```

**Response Format:**
```json
{
    "Request_id": "6118b54f-907b-4451-8d48-dd13d76033a5",
    "Datetime": "09-07-2025T12:34:55",
    "Location": "IIT Mumbai",
    "From": "userone.amd@gmail.com",
    "Attendees": [
        {
            "email": "userone.amd@gmail.com",
            "events": [
                {
                    "StartTime": "2025-07-17T10:30:00+05:30",
                    "EndTime": "2025-07-17T11:00:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": [
                        "userone.amd@gmail.com",
                        "usertwo.amd@gmail.com",
                        "userthree.amd@gmail.com"
                    ],
                    "Summary": "Agentic AI Project Status Update"
                }
            ]
        },
        {
            "email": "usertwo.amd@gmail.com",
            "events": [
                {
                    "StartTime": "2025-07-17T10:00:00+05:30",
                    "EndTime": "2025-07-17T10:30:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": [
                        "userone.amd@gmail.com",
                        "usertwo.amd@gmail.com",
                        "userthree.amd@gmail.com"
                    ],
                    "Summary": "Team Meet"
                },
                {
                    "StartTime": "2025-07-17T10:30:00+05:30",
                    "EndTime": "2025-07-17T11:00:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": [
                        "userone.amd@gmail.com",
                        "usertwo.amd@gmail.com",
                        "userthree.amd@gmail.com"
                    ],
                    "Summary": "Agentic AI Project Status Update"
                }
            ]
        },
        {
            "email": "userthree.amd@gmail.com",
            "events": [
                {
                    "StartTime": "2025-07-17T10:00:00+05:30",
                    "EndTime": "2025-07-17T10:30:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": [
                        "userone.amd@gmail.com",
                        "usertwo.amd@gmail.com",
                        "userthree.amd@gmail.com"
                    ],
                    "Summary": "Team Meet"
                },
                {
                    "StartTime": "2025-07-17T13:00:00+05:30",
                    "EndTime": "2025-07-17T14:00:00+05:30",
                    "NumAttendees": 1,
                    "Attendees": [
                        "SELF"
                    ],
                    "Summary": "Lunch with Customers"
                },
                {
                    "StartTime": "2025-07-17T10:30:00+05:30",
                    "EndTime": "2025-07-17T11:00:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": [
                        "userone.amd@gmail.com",
                        "usertwo.amd@gmail.com",
                        "userthree.amd@gmail.com"
                    ],
                    "Summary": "Agentic AI Project Status Update"
                }
            ]
        }
    ],
    "Subject": "Agentic AI Project Status Update",
    "EmailContent": "Hi team, let's meet on Thursday for 30 minutes to discuss the status of Agentic AI Project.",
    "EventStart": "2025-07-17T10:30:00+05:30",
    "EventEnd": "2025-07-17T11:00:00+05:30",
    "Duration_mins": "30",
    "MetaData": {}
}
```

### Testing the API

Save the sample request as `sample_request.json`:

```bash
curl -X POST http://localhost:5000/schedule \
     -H "Content-Type: application/json" \
     -d @sample_request.json
```

## 🤖 LLM Model: DeepSeek-LLM-7B-Chat

### Why DeepSeek-LLM-7B-Chat?

1.Handles Long, Complex Contexts:
    Multi-Head Latent Attention (MLA) lets DeepSeek-7B process entire e-mail threads, multiple calendars, and extended conversations in a single pass—perfect for scheduling and conflict resolution.

2.Fast and Memory-Efficient:
    MLA technology means up to 5.8× faster inference and 93% less memory usage compared to standard models, so scheduling stays snappy even with large workloads.

3.128K Token Context Window:
    Native support for up to 128,000 tokens enables DeepSeek-7B to understand and reason over even the most detailed scheduling histories and requests.

4.Optimized for On-Prem Deployment:
    DeepSeek-7B’s efficient architecture runs smoothly on AMD MI300 hardware, enabling secure, real-time AI scheduling—no data leaves your servers.

## 🔮 Features

- **Natural Language Processing**: Understands free-form scheduling requests
- **Intelligent Conflict Resolution**: Automatically resolves calendar conflicts
- **Multi-User Coordination**: Handles complex attendee scheduling
- **Time Zone Awareness**: Supports global team coordination
- **Real-time Optimization**: Continuously optimizes calendar efficiency
- **RESTful API**: Easy integration with existing systems

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes 
4. Push to the branch
5. Open a Pull Request


## 🎯 AMD MI300 GPU Hackathon

This project was developed for the AMD MI300 GPU Hackathon, showcasing the power of AI-driven automation in solving real-world productivity challenges.

---

**Built with ❤️ for the AMD MI300 GPU Hackathon**