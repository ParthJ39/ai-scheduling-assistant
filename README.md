# Agentic AI Meeting Scheduler

**AMD MI300 GPU HACKATHON PROJECT**

An intelligent meeting coordination system that autonomously schedules meetings, resolves conflicts, and optimizes calendars using natural language processing and AI-powered decision making.

## 🚀 Problem Statement

Today's meeting coordination is bogged down by time-consuming back-and-forth, manual conflict resolution, and inefficient calendar use—challenges our AI assistant solves by autonomously scheduling meetings, rescheduling conflicts, and optimizing calendars for maximum efficiency.

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

### 3. Environment Configuration

Create a `.env` file with the following variables:

```bash
# Flask API Configuration
FLASK_APP=app.py
FLASK_ENV=development
API_HOST=0.0.0.0
API_PORT=5000

# vLLM Configuration
VLLM_HOST=localhost
VLLM_PORT=8000
MODEL_NAME=deepseek-ai/deepseek-llm-7b-chat
```

### 4. Start the vLLM Server
vLLM is a high-performance inference engine that delivers up to 24x higher throughput than standard HuggingFace implementations through advanced memory management and continuous batching. Its PagedAttention algorithm dramatically reduces memory fragmentation, enabling efficient serving of large language models with minimal latency—perfect for real-time scheduling requests.

```bash
vllm serve \
  --model $MODEL_NAME \
  --host $VLLM_HOST \
  --port $VLLM_PORT
```

### 5. Run the Flask Application

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
  "EventStart": "2025-07-17T10:30:00+05:30",
  "EventEnd": "2025-07-17T11:00:00+05:30",
  "Subject": "Agentic AI Project Status Update",
  "Location": "IIT Mumbai",
  "Attendees": [
    { "email": "userone.amd@gmail.com" },
    { "email": "usertwo.amd@gmail.com" },
    { "email": "userthree.amd@gmail.com" }
  ],
  "Status": "Scheduled"
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

1. **Multilingual Excellence**: 7-billion-parameter model trained on 2+ trillion tokens in English and Chinese, providing deep understanding of scheduling language across cultures.

2. **Optimized for Chat**: Fine-tuned using supervised learning and Direct Preference Optimization, making it exceptionally skilled at:
   - Interpreting free-form meeting requests
   - Conditional rescheduling logic
   - Understanding nuanced calendar constraints

3. **Performance Optimized**: Architecture based on scaling-law research delivers optimal balance between depth and efficiency, enabling:
   - Sub-second inference times
   - High-throughput processing with vLLM
   - Real-time scheduling responses

4. **Cost-Effective**: Delivers equivalent fidelity to larger models while dramatically reducing:
   - Hardware requirements
   - Operational costs
   - Response latency

5. **Global Team Ready**: Bilingual training ensures robust performance across international teams and cross-cultural contexts.

## 🚦 Getting Started

1. **Prerequisites**:
   - Python 3.8+
   - CUDA-compatible GPU (for optimal performance)
   - 16GB+ RAM recommended

2. **Quick Start**:
   ```bash
   # Clone and setup
   git clone https://github.com/your-org/agentic-ai-scheduler.git
   cd agentic-ai-scheduler
   python3 -m venv venv && source venv/bin/activate
   
   # Install and run
   pip install -r requirements.txt
   python app.py
   ```

3. **Test the System**:
   ```bash
   curl -X POST http://localhost:5000/schedule \
        -H "Content-Type: application/json" \
        -d @sample_request.json
   ```

## 🔮 Features

- **Natural Language Processing**: Understands free-form scheduling requests
- **Intelligent Conflict Resolution**: Automatically resolves calendar conflicts
- **Multi-User Coordination**: Handles complex attendee scheduling
- **Time Zone Awareness**: Supports global team coordination
- **Real-time Optimization**: Continuously optimizes calendar efficiency
- **RESTful API**: Easy integration with existing systems

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## 🎯 AMD MI300 GPU Hackathon

This project was developed for the AMD MI300 GPU Hackathon, showcasing the power of AI-driven automation in solving real-world productivity challenges.

---

**Built with ❤️ for the AMD MI300 GPU Hackathon**