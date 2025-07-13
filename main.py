from flask import Flask, request, jsonify
import asyncio
import traceback
import time
from coordinator_agent import CoordinatorAgent
from json_validator import sanitize_json_request

app = Flask(__name__)

coordinator = CoordinatorAgent()

@app.route('/receive', methods=['POST'])
def receive():
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        request_id = data.get('Request_id', 'unknown')
        print(f"[{time.time():.3f}] Processing: {request_id}")
        
        sanitized_data = sanitize_json_request(data)
        
        result = asyncio.run(coordinator.schedule_meeting(sanitized_data))
        
        elapsed = time.time() - start_time
        success = result.get('EventStart') is not None and 'error' not in result
        
        if success:
            print(f"[{time.time():.3f}] Completed in {elapsed:.2f}s")
            print(f"Success: {result['EventStart']} to {result['EventEnd']}")
        else:
            print(f"[{time.time():.3f}] Completed in {elapsed:.2f}s")
            print(f"Failed: {result.get('error', 'Unknown error')}")
        
        return jsonify(result)
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{time.time():.3f}] Error after {elapsed:.2f}s: {e}")
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "Request_id": request.get_json().get('Request_id', 'unknown') if request.get_json() else 'unknown'
        }), 500


if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=5000, debug=True)