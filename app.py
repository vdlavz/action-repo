import os
import logging
import requests
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Default webhook URL - can be overridden via environment variable
DEFAULT_WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://httpbin.org/post")

@app.route('/')
def index():
    """Render the main webhook testing form"""
    return render_template('index.html', default_webhook_url=DEFAULT_WEBHOOK_URL)

@app.route('/test-webhook', methods=['POST'])
def test_webhook():
    """Handle webhook testing form submission"""
    try:
        # Get form data
        webhook_url = request.form.get('webhook_url', '').strip()
        event = request.form.get('event', '').strip()
        sender = request.form.get('sender', '').strip()
        message = request.form.get('message', '').strip()
        
        # Validate required fields
        if not webhook_url:
            return jsonify({
                'success': False,
                'error': 'Webhook URL is required'
            }), 400
        
        if not event:
            return jsonify({
                'success': False,
                'error': 'Event is required'
            }), 400
        
        # Prepare webhook payload
        payload = {
            'event': event,
            'sender': sender,
            'message': message,
            'timestamp': requests.utils.default_user_agent()  # Add timestamp using requests utility
        }
        
        # Add timestamp manually since we can't use datetime
        import time
        payload['timestamp'] = int(time.time())
        
        # Set headers for JSON content
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Webhook-Tester/1.0'
        }
        
        # Make the webhook request with timeout
        app.logger.info(f"Sending webhook to: {webhook_url}")
        app.logger.debug(f"Payload: {payload}")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        
        # Log the response
        app.logger.info(f"Webhook response status: {response.status_code}")
        app.logger.debug(f"Webhook response: {response.text}")
        
        # Prepare response data
        response_data = {
            'success': True,
            'status_code': response.status_code,
            'status_text': response.reason,
            'response_headers': dict(response.headers),
            'response_body': response.text,
            'request_payload': payload
        }
        
        # Try to parse JSON response if possible
        try:
            response_data['response_json'] = response.json()
        except:
            response_data['response_json'] = None
        
        return jsonify(response_data)
        
    except requests.exceptions.Timeout:
        app.logger.error("Webhook request timed out")
        return jsonify({
            'success': False,
            'error': 'Request timed out (30 seconds)'
        }), 408
        
    except requests.exceptions.ConnectionError:
        app.logger.error("Connection error when calling webhook")
        return jsonify({
            'success': False,
            'error': 'Connection error - could not reach webhook URL'
        }), 503
        
    except requests.exceptions.InvalidURL:
        app.logger.error("Invalid webhook URL provided")
        return jsonify({
            'success': False,
            'error': 'Invalid webhook URL format'
        }), 400
        
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)
