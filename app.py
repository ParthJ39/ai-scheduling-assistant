import asyncio
import traceback
from logger import logger
from tests.mock_data import TEST_SCENARIOS
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


@app.route('/demo/<scenario_name>', methods=['GET'])
def demo_scenario(scenario_name):
    """Demo endpoint for testing scenarios"""
    if scenario_name not in TEST_SCENARIOS:
        available_scenarios = list(TEST_SCENARIOS.keys())
        return jsonify({
            "error": "Scenario not found",
            "available_scenarios": available_scenarios
        }), 404

    try:
        scenario_data = TEST_SCENARIOS[scenario_name]
        print(f"\nRunning Demo Scenario: {scenario_name}")
        print(f"Scenario description: {scenario_data.get('EmailContent', '')}")

        result = asyncio.run(coordinator.schedule_meeting(scenario_data))

        return jsonify({
            "scenario": scenario_name,
            "input": scenario_data,
            "result": result,
            "success": result.get('EventStart') is not None and 'error' not in result
        })

    except Exception as e:
        print(f"Demo scenario error: {e}")
        traceback.print_exc()
        return jsonify({
            "scenario": scenario_name,
            "error": str(e)
        }), 500
