#!/usr/bin/env python3
"""
Enhanced webhook server that integrates with DocuSync agents and Orkes workflows.
This server receives GitHub webhooks and triggers the complete documentation workflow.
"""

import os
import sys
import json
import hmac
import hashlib
import asyncio
from flask import Flask, request, jsonify
from datetime import datetime
from decouple import Config, RepositoryEnv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commit_watcher_agent import CommitWatcherAgent
from readme_updater_agent import ReadmeUpdaterAgent

# Load configuration
backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(backend_env_path):
    env_config = Config(RepositoryEnv(backend_env_path))
else:
    from decouple import config as env_config

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = env_config('GITHUB_WEBHOOK_SECRET', default='bahen')
GITHUB_TOKEN = env_config('GITHUB_TOKEN', default='')
GOOGLE_API_KEY = env_config('GOOGLE_API_KEY', default='')
PORT = int(env_config('WEBHOOK_PORT', default='5000'))

# Initialize agents (will be done on first request to avoid startup delay)
commit_agent = None
readme_agent = None

# Track recently processed PRs to prevent infinite loops
recent_pr_updates = {}  # {repo/pr_number: timestamp}

def init_agents():
    """Initialize DocuSync agents lazily."""
    global commit_agent, readme_agent
    
    if not commit_agent:
        print("🔧 Initializing DocuSync agents...")
        try:
            commit_agent = CommitWatcherAgent(GITHUB_TOKEN)
            readme_agent = ReadmeUpdaterAgent(GITHUB_TOKEN)
            print("✅ Agents initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize agents: {e}")
            return False
    
    return True

def verify_signature(payload_body, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256 signature."""
    if not signature_header or not WEBHOOK_SECRET:
        return True  # Skip verification if no secret configured
    
    try:
        hash_object = hmac.new(
            WEBHOOK_SECRET.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        return hmac.compare_digest(expected_signature, signature_header)
    except Exception as e:
        print(f"❌ Signature verification error: {e}")
        return False

def check_commit_files_changed(owner, repo, commit_sha):
    """Check what files were changed in a specific commit."""
    try:
        import requests
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DocuSync-Agent"
        }
        
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            commit_data = response.json()
            files = commit_data.get('files', [])
            filenames = [f.get('filename', '') for f in files]
            return filenames
    except Exception as e:
        print(f"⚠️  Error fetching commit files: {e}")
    
    return []

def cleanup_old_pr_updates():
    """Clean up old entries from recent_pr_updates to prevent memory leaks."""
    global recent_pr_updates
    current_time = datetime.now()
    
    # Remove entries older than 10 minutes
    keys_to_remove = []
    for pr_key, timestamp in recent_pr_updates.items():
        if (current_time - timestamp).total_seconds() > 600:  # 10 minutes
            keys_to_remove.append(pr_key)
    
    for key in keys_to_remove:
        del recent_pr_updates[key]

def should_ignore_webhook(payload):
    """Check if webhook should be ignored to prevent infinite loops."""
    global recent_pr_updates
    
    # Clean up old entries first
    cleanup_old_pr_updates()
    
    # For pull_request events, check if the changes are only to README.md
    if 'pull_request' in payload:
        action = payload.get('action', '')
        repo_full_name = payload.get('repository', {}).get('full_name', '')
        pr_number = payload.get('pull_request', {}).get('number')
        
        if not repo_full_name or not pr_number:
            return False
        
        pr_key = f"{repo_full_name}/{pr_number}"
        current_time = datetime.now()
        
        # Check if we recently processed this PR (within last 3 minutes)
        if pr_key in recent_pr_updates:
            time_diff = current_time - recent_pr_updates[pr_key]
            if time_diff.total_seconds() < 180:  # 3 minutes
                print(f"🚫 Ignoring webhook - recently processed {pr_key} ({time_diff.total_seconds():.1f}s ago)")
                return True
        
        # For synchronize events (new commits), check what files were changed
        if action == 'synchronize':
            try:
                owner, repo = repo_full_name.split('/')
                
                # Get the latest commit SHA
                head_commit = payload.get('pull_request', {}).get('head', {}).get('sha')
                
                if head_commit:
                    # Check what files were changed in this commit
                    changed_files = check_commit_files_changed(owner, repo, head_commit)
                    
                    # If only README.md or other documentation files were changed, likely our automation
                    if changed_files:
                        non_doc_files = [f for f in changed_files if not any(
                            doc_pattern in f.lower() for doc_pattern in [
                                'readme.md', 'readme.rst', 'readme.txt',
                                'docs/', 'documentation/', '.md'
                            ]
                        )]
                        
                        # If no non-documentation files were changed, ignore this webhook
                        if not non_doc_files:
                            print(f"🚫 Ignoring webhook - only documentation files changed: {changed_files}")
                            return True
                        
                        print(f"✅ Processing webhook - non-doc files changed: {non_doc_files}")
                        
            except Exception as e:
                print(f"⚠️  Error checking webhook ignore conditions: {e}")
    
    return False

def process_webhook_async(event_type, payload):
    """Process webhook asynchronously to avoid blocking the HTTP response."""
    
    if event_type == 'pull_request':
        action = payload.get('action', '')
        
        # Check if we should ignore this webhook to prevent infinite loops
        if should_ignore_webhook(payload):
            return
        
        # Only process certain PR actions
        if action in ['opened', 'synchronize', 'edited', 'reopened']:
            print(f"🔄 Processing PR webhook: {action}")
            
            try:
                # Initialize agents if needed
                if not init_agents():
                    print("❌ Failed to initialize agents for processing")
                    return
                
                # Record that we're processing this PR
                repo_full_name = payload.get('repository', {}).get('full_name', '')
                pr_number = payload.get('pull_request', {}).get('number')
                if repo_full_name and pr_number:
                    pr_key = f"{repo_full_name}/{pr_number}"
                    recent_pr_updates[pr_key] = datetime.now()
                    print(f"🔒 Recorded processing start for {pr_key}")
                
                # Step 1: Analyze the PR
                print("📊 Step 1: Analyzing PR with commit watcher...")
                pr_analysis = commit_agent.analyze_pr_webhook(payload)
                
                if 'error' in pr_analysis:
                    print(f"❌ PR analysis failed: {pr_analysis['error']}")
                    return
                
                print(f"✅ PR analysis complete: {pr_analysis['repository']}#{pr_analysis['pr_number']}")
                print(f"   Priority: {pr_analysis['priority']}")
                print(f"   Requires docs: {pr_analysis['requires_documentation']}")
                
                # Step 2: Get PR diff for better AI analysis
                print("📄 Step 2a: Fetching PR diff for enhanced analysis...")
                pr_diff = None
                try:
                    repo_full_name = pr_analysis.get('repository', '')
                    pr_number = pr_analysis.get('pr_number')
                    if repo_full_name and pr_number:
                        owner, repo = repo_full_name.split('/')
                        pr_diff = commit_agent.github_client.get_pr_diff(owner, repo, pr_number)
                        if pr_diff:
                            print(f"✅ PR diff fetched ({len(pr_diff)} characters)")
                        else:
                            print("⚠️  Could not fetch PR diff")
                except Exception as e:
                    print(f"⚠️  Error fetching PR diff: {e}")
                
                # Step 2b: Generate real AI analysis with Google Gemini
                print("🤖 Step 2b: Generating AI documentation with Google Gemini...")
                
                ai_comment = generate_ai_documentation_with_gemini(pr_analysis, pr_diff)
                
                # Step 3: Update README.md on PR branch instead of posting comment
                if pr_analysis.get('requires_documentation', False) or True:  # Always update for demo
                    print("📚 Step 3: Updating README.md on PR branch...")
                    
                    result = readme_agent.update_readme_with_ai_insights(
                        pr_analysis=pr_analysis,
                        ai_comment=ai_comment,
                        webhook_payload=payload
                    )
                    
                    if result.get('status') == 'success':
                        print(f"✅ README.md updated successfully on branch {result.get('branch')}")
                        print(f"🔗 View: https://github.com/{pr_analysis['repository']}/pull/{pr_analysis['pr_number']}")
                    else:
                        print(f"❌ Failed to update README.md: {result.get('message', 'Unknown error')}")
                else:
                    print("⏭️  Skipping README update - no documentation required")
                
            except Exception as e:
                print(f"❌ Error processing PR webhook: {e}")
        else:
            print(f"⏭️  Skipping PR action: {action}")

def generate_ai_documentation_with_gemini(pr_analysis, pr_diff=None):
    """Generate AI-powered documentation using Google Gemini."""
    
    if not GOOGLE_API_KEY:
        print("⚠️  No Google API key configured, falling back to simulation")
        return generate_ai_comment_fallback(pr_analysis)
    
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare the prompt with PR analysis data
        repository = pr_analysis.get('repository', 'Unknown Repository')
        pr_number = pr_analysis.get('pr_number', 'Unknown')
        priority = pr_analysis.get('priority', 'medium')
        requires_docs = pr_analysis.get('requires_documentation', False)
        files_changed = pr_analysis.get('changes_summary', {}).get('files_changed', 0)
        suggested_actions = pr_analysis.get('suggested_actions', [])
        
        # Create detailed prompt for Gemini
        prompt = f"""You are DocuSync AI, an expert technical documentation assistant. Analyze this GitHub Pull Request and create comprehensive documentation insights.

**Repository**: {repository}
**PR Number**: #{pr_number}
**Priority**: {priority}
**Files Changed**: {files_changed}
**Requires Documentation**: {requires_docs}
**Suggested Actions**: {', '.join(suggested_actions) if suggested_actions else 'None specified'}

**PR Diff (if available)**: 
{pr_diff[:2000] if pr_diff else 'Diff not available'}

Please generate a comprehensive documentation analysis that includes:

1. **Change Analysis**: Analyze the technical impact and scope of changes
2. **Documentation Requirements**: Specific documentation updates needed
3. **Implementation Insights**: Technical details about what was changed
4. **Developer Guidance**: Clear next steps for the development team
5. **Quality Assessment**: Overall code quality and documentation readiness

Format your response as a detailed technical analysis that will be added to the repository's README.md file. Use clear headings, bullet points, and actionable recommendations.

Focus on being helpful, technical, and actionable. This will be read by developers working on the project."""

        # Generate content with Gemini
        print("🤖 Generating documentation with Google Gemini...")
        response = model.generate_content(prompt)
        
        if response and response.text:
            print("✅ Gemini response generated successfully")
            return {"output": response.text}
        else:
            print("⚠️  Empty response from Gemini, using fallback")
            return generate_ai_comment_fallback(pr_analysis)
            
    except Exception as e:
        print(f"❌ Error generating with Gemini: {e}")
        print("🔄 Falling back to simulation")
        return generate_ai_comment_fallback(pr_analysis)

def generate_ai_comment_fallback(pr_analysis):
    """Fallback AI comment generation when Gemini is not available."""
    
    priority = pr_analysis.get('priority', 'unknown')
    requires_docs = pr_analysis.get('requires_documentation', False)
    files_changed = pr_analysis.get('changes_summary', {}).get('files_changed', 0)
    
    if requires_docs:
        comment = f"""## 🤖 DocuSync AI Analysis

### 📊 Technical Change Assessment
This pull request has been automatically analyzed and contains changes that impact documentation.

**Analysis Summary:**
- **Impact Priority**: {priority.title()}
- **Files Modified**: {files_changed}
- **Documentation Updates Required**: ✅ Yes

### 🔧 Documentation Requirements
Based on the automated code analysis, the following documentation updates are recommended:

{chr(10).join(f"• {action}" for action in pr_analysis.get('suggested_actions', ['Update relevant documentation sections', 'Review API changes', 'Verify code examples']))}

### 🎯 Implementation Guidance
1. **Code Review**: Examine changes for new public APIs or modified interfaces
2. **Documentation Updates**: Update affected documentation sections
3. **Example Validation**: Test and update code examples as needed
4. **Changelog Updates**: Document user-facing changes

### ⚡ Action Items
- [ ] Update README.md with new feature descriptions
- [ ] Refresh API documentation for modified endpoints
- [ ] Validate existing code examples still work
- [ ] Update configuration guides if settings changed

*Generated by DocuSync AI - Automated documentation analysis*"""
    else:
        comment = f"""## 🤖 DocuSync AI Analysis

### 📊 Technical Change Assessment
This pull request has been automatically analyzed and appears to be maintenance-focused.

**Analysis Summary:**
- **Impact Priority**: {priority.title()}
- **Files Modified**: {files_changed}
- **Documentation Updates Required**: ✅ Minimal or none needed

### 🎯 Change Classification
The modifications in this PR appear to be:
- Internal refactoring or code improvements
- Bug fixes that don't affect public interfaces
- Maintenance updates with contained scope

### ✨ Quality Assessment
This PR demonstrates good development practices with focused, contained changes. No significant documentation updates are required based on the automated analysis.

*Generated by DocuSync AI - Automated documentation analysis*"""

    return {"output": comment}

@app.route('/webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events and trigger DocuSync workflow."""
    
    # Get headers
    signature = request.headers.get('X-Hub-Signature-256')
    event_type = request.headers.get('X-GitHub-Event')
    delivery_id = request.headers.get('X-GitHub-Delivery')
    
    # Verify signature
    if not verify_signature(request.data, signature):
        print("❌ Webhook signature verification failed!")
        return jsonify({"error": "Unauthorized"}), 401
    
    # Parse payload
    try:
        payload = request.get_json()
    except Exception as e:
        print(f"❌ Failed to parse JSON payload: {e}")
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Log webhook receipt
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🎣 GitHub Webhook Received at {timestamp}")
    print(f"📋 Event Type: {event_type}")
    print(f"🆔 Delivery ID: {delivery_id}")
    
    if payload and 'repository' in payload:
        repo_name = payload['repository']['full_name']
        print(f"📁 Repository: {repo_name}")
        
        if event_type == 'pull_request':
            action = payload.get('action', 'unknown')
            pr_number = payload['pull_request']['number']
            pr_title = payload['pull_request']['title']
            print(f"🔀 Pull Request #{pr_number}: {action}")
            print(f"📄 Title: {pr_title}")
            
            # Process the webhook asynchronously
            import threading
            processing_thread = threading.Thread(
                target=process_webhook_async,
                args=(event_type, payload)
            )
            processing_thread.start()
            
        elif event_type == 'push':
            ref = payload.get('ref', 'unknown')
            commits = payload.get('commits', [])
            print(f"🔄 Push to: {ref}")
            print(f"📝 Commits: {len(commits)}")
        
        print(f"📦 Payload size: {len(json.dumps(payload))} bytes")
    
    print("-" * 60)
    
    # Return immediate response
    response_data = {
        "status": "success", 
        "message": "Webhook received and processing started",
        "event_type": event_type,
        "delivery_id": delivery_id,
        "timestamp": timestamp
    }
    
    return jsonify(response_data), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "agents_initialized": commit_agent is not None and readme_agent is not None,
        "github_token_configured": bool(GITHUB_TOKEN),
        "webhook_secret_configured": bool(WEBHOOK_SECRET),
        "google_ai_configured": bool(GOOGLE_API_KEY)
    }), 200

@app.route('/status', methods=['GET'])
def status():
    """Detailed status endpoint."""
    return jsonify({
        "service": "DocuSync Webhook Server",
        "status": "running",
        "agents": {
            "commit_watcher": "initialized" if commit_agent else "not initialized",
            "readme_updater": "initialized" if readme_agent else "not initialized"
        },
        "configuration": {
            "github_token": "configured" if GITHUB_TOKEN else "missing",
            "webhook_secret": "configured" if WEBHOOK_SECRET else "missing",
            "google_ai": "configured" if GOOGLE_API_KEY else "missing",
            "port": PORT
        },
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health", 
            "status": "/status"
        },
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Index page with server information."""
    return f"""
    <h1>🚀 DocuSync Webhook Server</h1>
    <p><strong>Status:</strong> Running and ready to receive webhooks!</p>
    
    <h2>📡 Endpoints</h2>
    <ul>
        <li><strong>Webhook:</strong> <code>POST /webhook</code> - GitHub webhook endpoint</li>
        <li><strong>Health:</strong> <code>GET /health</code> - Health check</li>
        <li><strong>Status:</strong> <code>GET /status</code> - Detailed status</li>
    </ul>
    
    <h2>⚙️ Configuration</h2>
    <ul>
        <li><strong>Port:</strong> {PORT}</li>
        <li><strong>GitHub Token:</strong> {'✅ Configured' if GITHUB_TOKEN else '❌ Missing'}</li>
        <li><strong>Webhook Secret:</strong> {'✅ Configured' if WEBHOOK_SECRET else '❌ Missing'}</li>
        <li><strong>Google AI:</strong> {'✅ Configured' if GOOGLE_API_KEY else '❌ Missing'}</li>
        <li><strong>Agents:</strong> {'✅ Ready' if commit_agent and readme_agent else '⏳ Will initialize on first request'}</li>
    </ul>
    
    <h2>🔗 GitHub Webhook URL</h2>
    <p>Configure your GitHub repository webhook to point to:</p>
    <code>https://your-domain.com/webhook</code>
    
    <h2>🤖 Workflow</h2>
    <p>When a PR webhook is received, this server will:</p>
    <ol>
        <li>📊 Analyze the PR changes</li>
        <li>🤖 Generate AI-powered documentation insights</li>
        <li>📚 Update README.md file on the PR branch with documentation enhancements</li>
    </ol>
    
    <p><em>Powered by DocuSync AI with Google Gemini</em></p>
    """

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 Starting DocuSync Integrated Webhook Server")
    print("=" * 80)
    print(f"📡 Webhook endpoint: http://0.0.0.0:{PORT}/webhook")
    print(f"🔍 Health check: http://0.0.0.0:{PORT}/health")
    print(f"📊 Status endpoint: http://0.0.0.0:{PORT}/status")
    print(f"🏠 Index page: http://0.0.0.0:{PORT}/")
    print()
    print("⚙️ Configuration:")
    print(f"   GitHub Token: {'✅ Configured' if GITHUB_TOKEN else '❌ Missing'}")  
    print(f"   Webhook Secret: {'✅ Configured' if WEBHOOK_SECRET else '❌ Not set'}")
    print(f"   Google AI: {'✅ Configured' if GOOGLE_API_KEY else '❌ Missing'}")
    print(f"   Port: {PORT}")
    print()
    print("🎯 To configure GitHub webhook:")
    print(f"   1. Go to your repository settings")
    print(f"   2. Add webhook URL: https://your-domain.com/webhook")
    print(f"   3. Set content type: application/json")
    print(f"   4. Select events: Pull requests")
    print(f"   5. Set secret: {WEBHOOK_SECRET}")
    print()
    print("🤖 This server will automatically:")
    print("   • Receive GitHub PR webhooks")
    print("   • Analyze changes with DocuSync agents")
    print("   • Generate AI-powered documentation insights using Google Gemini")
    print("   • Update README.md files on PR branches with enhanced documentation")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)