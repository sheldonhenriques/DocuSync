#!/usr/bin/env python3
import json
import hmac
import hashlib
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

WEBHOOK_SECRET = "bahen"  # Replace with your actual secret

def verify_signature(payload_body, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256 signature."""
    if not signature_header:
        print("❌ No signature header found")
        return False
    
    hash_object = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    print(f"🔐 Expected signature: {expected_signature}")
    print(f"🔐 Received signature: {signature_header}")
    
    is_valid = hmac.compare_digest(expected_signature, signature_header)
    print(f"🔐 Signature valid: {is_valid}")
    
    return is_valid

@app.route('/webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events."""
    
    # Get the signature from the header
    signature = request.headers.get('X-Hub-Signature-256')
    
    # Verify the webhook signature (optional but recommended)
    if WEBHOOK_SECRET != "your_webhook_secret_here":
        if not verify_signature(request.data, signature):
            print("❌ Webhook signature verification failed!")
            return jsonify({"error": "Unauthorized"}), 401
    
    # Get the event type
    event_type = request.headers.get('X-GitHub-Event')
    
    # Parse the JSON payload
    try:
        payload = request.get_json()
    except Exception as e:
        print(f"❌ Failed to parse JSON payload: {e}")
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Print webhook information
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🎣 GitHub Webhook Received at {timestamp}")
    print(f"📋 Event Type: {event_type}")
    
    if payload:
        # Print repository information if available
        if 'repository' in payload:
            repo_name = payload['repository']['full_name']
            print(f"📁 Repository: {repo_name}")
        
        # Print specific event details
        if event_type == 'push':
            ref = payload.get('ref', 'unknown')
            commits = payload.get('commits', [])
            print(f"🔄 Push to: {ref}")
            print(f"📝 Commits: {len(commits)}")
            
        elif event_type == 'pull_request':
            action = payload.get('action', 'unknown')
            pr_number = payload['pull_request']['number']
            pr_title = payload['pull_request']['title']
            print(f"🔀 Pull Request #{pr_number}: {action}")
            print(f"📄 Title: {pr_title}")
            
        elif event_type == 'issues':
            action = payload.get('action', 'unknown')
            issue_number = payload['issue']['number']
            issue_title = payload['issue']['title']
            print(f"🐛 Issue #{issue_number}: {action}")
            print(f"📄 Title: {issue_title}")
        
        # Print raw payload for debugging (optional)
        print(f"📦 Payload size: {len(json.dumps(payload))} bytes")
    
    print("-" * 50)
    
    return jsonify({"status": "success", "message": "Webhook received"}), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

@app.route('/', methods=['GET'])
def index():
    """Simple index page."""
    return """
    <h1>GitHub Webhook Server</h1>
    <p>Server is running and ready to receive webhooks!</p>
    <p>Webhook endpoint: <code>/webhook</code></p>
    <p>Health check: <code>/health</code></p>
    """

if __name__ == '__main__':
    print("🚀 Starting GitHub Webhook Server...")
    print("📡 Webhook endpoint: http://localhost:5000/webhook")
    print("🔍 Health check: http://localhost:5000/health")
    print("⚙️  Configure your GitHub webhook to point to this server")
    print("-" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)