from flask import Flask, request, jsonify
from sports_agent import build_payload
import requests
import os

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "service": "sports-agent",
        "endpoints": ["/test-api", "/run"]
    })

@app.route("/test-api", methods=["GET"])
def test_api():
    """Test Sportsbook API to find working endpoint"""
    api_key = os.getenv('RAPIDAPI_KEY')
    
    if not api_key:
        return jsonify({
            'status': 'error',
            'message': 'RAPIDAPI_KEY not set'
        }), 500
    
    test_configs = [
        {
            'name': 'v0/events/ with americanfootball_nfl',
            'url': 'https://sportsbook-api2.p.rapidapi.com/v0/events/',
            'params': {'sport': 'americanfootball_nfl'}
        },
        {
            'name': 'v0/events without slash',
            'url': 'https://sportsbook-api2.p.rapidapi.com/v0/events',
            'params': {'sport': 'americanfootball_nfl'}
        },
        {
            'name': 'v1/events',
            'url': 'https://sportsbook-api2.p.rapidapi.com/v1/events',
            'params': {'sport': 'americanfootball_nfl'}
        }
    ]
    
    results = []
    working_config = None
    
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'sportsbook-api2.p.rapidapi.com'
    }
    
    for config in test_configs:
        try:
            response = requests.get(
                config['url'],
                headers=headers,
                params=config['params'],
                timeout=10
            )
            
            result = {
                'test': config['name'],
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
            
            if response.status_code == 200:
                data = response.json()
                events_count = len(data.get('events', [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
                result['events_count'] = events_count
                result['has_data'] = events_count > 0
                
                if events_count > 0 and not working_config:
                    working_config = config
                    result['✅'] = 'USE THIS ONE!'
            else:
                result['error'] = response.text[:200]
            
            results.append(result)
                
        except Exception as e:
            results.append({
                'test': config['name'],
                'error': str(e)
            })
    
    recommendation = None
    if working_config:
        recommendation = {
            'message': '✅ WORKING ENDPOINT FOUND',
            'update_sportsbook_api': f"url = f'https://{{API_HOST}}{working_config['url'].split('.com')[1]}'",
            'sport_param': working_config['params']['sport']
        }
    else:
        recommendation = {
            'message': '❌ No working endpoint',
            'action': 'Check RapidAPI dashboard'
        }
    
    return jsonify({
        'status': 'test_complete',
        'results': results,
        'recommendation': recommendation
    })

@app.route("/run", methods=["POST"])
def run():
    """Main endpoint for ChatGPT to fetch sports data"""
    try:
        body = request.get_json(force=True) or {}
        sport = body.get("sport", "nfl")
        allow_api = body.get("allow_api", True)
        max_games = body.get("max_games", 10)
        
        payload = build_payload(
            sport,
            allow_api=allow_api,
            max_games=max_games
        )
        return jsonify(payload)
        
    except Exception as e:
        app.logger.error(f"/run failed: {e}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
