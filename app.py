from flask import Flask, request, jsonify
from sports_agent import build_payload
import requests
import os
import io
from openpyxl import Workbook

app = Flask(__name__)

@app.route("/")
def home():
    return "Sports Agent API is live!"

@app.route("/test-api", methods=["GET"])
def test_api():
    """Temporary endpoint to test Sportsbook API connection"""
    api_key = os.getenv('RAPIDAPI_KEY')
    
    if not api_key:
        return jsonify({
            'status': 'error',
            'message': 'RAPIDAPI_KEY not set in environment variables'
        }), 500
    
    # Test different endpoint variations
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
        },
        {
            'name': 'v0/events/ no params',
            'url': 'https://sportsbook-api2.p.rapidapi.com/v0/events/',
            'params': {}
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
                'url': config['url'],
                'params': config['params'],
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result['response_keys'] = list(data.keys()) if isinstance(data, dict) else 'array'
                    
                    # Count events
                    if isinstance(data, dict):
                        events_count = len(data.get('events', []))
                    elif isinstance(data, list):
                        events_count = len(data)
                    else:
                        events_count = 0
                    
                    result['events_count'] = events_count
                    result['has_data'] = events_count > 0
                    
                    # Sample of first event
                    if isinstance(data, dict) and 'events' in data and len(data['events']) > 0:
                        first_event = data['events'][0]
                        result['sample_event'] = {
                            'keys': list(first_event.keys()),
                            'name': first_event.get('name', 'N/A')
                        }
                    
                    # Store first working config
                    if events_count > 0 and not working_config:
                        working_config = config
                        
                except Exception as e:
                    result['json_error'] = str(e)
                    result['response_text'] = response.text[:300]
            else:
                result['error'] = response.text[:200]
            
            results.append(result)
            
            # If we found a working endpoint with data, mark it
            if response.status_code == 200 and result.get('has_data'):
                result['✅'] = 'WORKING - USE THIS!'
                
        except Exception as e:
            results.append({
                'test': config['name'],
                'url': config['url'],
                'error': str(e),
                'success': False
            })
    
    # Prepare recommendation
    recommendation = None
    if working_config:
        # Extract base URL and endpoint path
        full_url = working_config['url']
        base_url = full_url.replace('/events/', '').replace('/events', '')
        
        recommendation = {
            'message': '✅ FOUND WORKING ENDPOINT!',
            'base_url': base_url,
            'endpoint': '/events/' if full_url.endswith('/') else '/events',
            'sport_param': working_config['params'].get('sport'),
            'next_steps': [
                'Update sportsbook_api.py:',
                f"  BASE_URL = '{base_url}'",
                f"  sport_key = '{working_config['params'].get('sport')}'",
                'Then redeploy to Render'
            ]
        }
    else:
        recommendation = {
            'message': '❌ No working endpoint found',
            'next_steps': [
                'Check if RAPIDAPI_KEY is valid',
                'Verify subscription is active',
                'Check RapidAPI dashboard for correct endpoints'
            ]
        }
    
    return jsonify({
        'status': 'test_complete',
        'api_key_present': True,
        'api_key_preview': api_key[:10] + '...' if len(api_key) > 10 else 'too_short',
        'tests_run': len(results),
        'results': results,
        'recommendation': recommendation
    })

@app.route("/run", methods=["POST"])
def run():
    try:
        body = request.get_json(force=True)
        sport = body.get("sport", "nfl")
        allow_api = body.get("allow_api", False)
        game_filter = body.get("game_filter")
        max_games = body.get("max_games")
        payload = build_payload(
            sport,
            allow_api=allow_api,
            max_games=max_games
        )
        return jsonify(payload)
    except Exception as e:
        app.logger.error(f"/run failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/excel", methods=["POST"])
def excel():
    try:
        body = request.get_json(force=True)
        payload = build_payload(
            body.get("sport", "nfl"),
            allow_api=body.get("allow_api", False),
            max_games=body.get("max_games")
        )
        
        # Create Excel file from payload
        wb = Workbook()
        ws = wb.active
        ws.title = "Sports Data"
        
        # Write games
        if payload.get('games'):
            ws.append(['Games'])
            ws.append(list(payload['games'][0].keys()) if payload['games'] else [])
            for game in payload['games']:
                ws.append(list(game.values()))
        
        # Save to bytes
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        return excel_buffer.getvalue(), 200, {
            "Content-Disposition": "attachment; filename=output.xlsx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
    except Exception as e:
        app.logger.error(f"/excel failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
