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
        "endpoints": [
            "/test-api (GET) - Test API connection",
            "/run (POST) - Get sports data"
        ]
    })

@app.route("/test-api", methods=["GET"])
def test_api():
    """Test endpoint to find working Sportsbook API configuration"""
    api_key = os.getenv('RAPIDAPI_KEY')
    
    if not api_key:
        return jsonify({
            'status': 'error',
            'message': 'RAPIDAPI_KEY not set in environment'
        }), 500
    
    test_configs = [
        {
            'name': 'v0/events/ with americanfootball_nfl',
            'url': 'https://sportsbook-api2.p.rapidapi.com/v0/events/',
            'params': {'sport': 'americanfootball_nfl'}
        },
        {
            'name': 'v0/events without trailing slash',
            'url': 'https://sportsbook-api2.p.rapidapi.com/v0/events',
            'params': {'sport': 'americanfootball_nfl'}
        },
        {
            'name': 'v1/events',
            'url': 'https://sportsbook-api2.p.rapidapi.com/v1/events',
            'params': {'sport': 'americanfootball_nfl'}
        },
        {
            'name': 'v0/events/ with sport=nfl',
            'url': 'https://sportsbook-api2.p.rapidapi.com/v0/events/',
            'params': {'sport': 'nfl'}
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
                try:
                    data = response.json()
                    events_count = len(data.get('events', [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
                    
                    result['events_count'] = events_count
                    result['has_data'] = events_count > 0
                    
                    if events_count > 0:
                        result['✅'] = 'WORKING!'
                        if not working_config:
                            working_config = config
                            
                except Exception as e:
                    result['error'] = str(e)
            else:
                result['error'] = response.text[:200]
            
            results.append(result)
                
        except Exception as e:
            results.append({
                'test': config['name'],
                'error': str(e),
                'success': False
            })
    
    recommendation = None
    if working_config:
        recommendation = {
            'message': '✅ FOUND WORKING ENDPOINT!',
            'url': working_config['url'],
            'sport_param': working_config['params'].get('sport'),
            'next_step': 'This configuration is already in your updated sportsbook_api.py'
        }
    else:
        recommendation = {
            'message': '❌ No working endpoint found',
            'action': 'Check RapidAPI subscription and key'
        }
    
    return jsonify({
        'status': 'test_complete',
        'results': results,
        'recommendation': recommendation
    })

@app.route("/run", methods=["POST"])
def run():
    """
    Main endpoint for ChatGPT integration.
    
    POST Body:
    {
        "sport": "nfl",
        "allow_api": true,
        "max_games": 10
    }
    """
    try:
        body = request.get_json(force=True)
        sport = body.get("sport", "nfl")
        allow_api = body.get("allow_api", False)
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
