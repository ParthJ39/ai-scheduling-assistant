import json
import asyncio
import traceback
from logger import logger
from datetime import datetime
# from mock_data import TEST_SCENARIOS
from flask import Flask, request, jsonify
from resources.agents.coordinator_agent import CoordinatorAgent
from resources.utils.json_validator import clean_json_request

app = Flask(__name__)

# Initialize the coordinator
coordinator = CoordinatorAgent()


@app.route('/receive', methods=['POST'])
def receive():
    """Required endpoint for hackathon submission"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        logger.info(f"Received Request: {data.get('Request_id', 'unknown')}")
        logger.info(f"Email Content: {data.get('EmailContent', '')}")
        logger.info(f"Attendees: {len(data.get('Attendees', []))} participants")

        clean_json = clean_json_request(data)

        # agentic system calls
        result = asyncio.run(coordinator.schedule_meeting(clean_json))

        success = result.get('EventStart') is not None and 'error' not in result
        logger.info(f"Processing complete-Success: {success}")

        if success:
            logger.info(f"Scheduled: {result['EventStart']} to {result['EventEnd']}")

        return jsonify(result)

    except Exception as e:
        logger(f"Error processing request: {e}")
        traceback.print_exc()
        return jsonify({
            "error": "Error processing request.",
            "Request_id": request.get_json().get('Request_id', 'unknown') if request.get_json() else 'unknown'
        }), 500
