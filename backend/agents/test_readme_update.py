#!/usr/bin/env python3
"""
Test script to verify README update functionality works end-to-end.
"""

import os
import json
from datetime import datetime
from decouple import Config, RepositoryEnv

# Import our agents
from readme_updater_agent import ReadmeUpdaterAgent

def main():
    """Test the README update functionality."""
    
    print("🧪 Testing README Update Functionality")
    print("=" * 50)
    
    # Load config
    backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(backend_env_path):
        env_config = Config(RepositoryEnv(backend_env_path))
    else:
        from decouple import config as env_config
    
    github_token = env_config('GITHUB_TOKEN', default='')
    
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment")
        return
    
    # Initialize README updater agent
    print("🔧 Initializing README Updater Agent...")
    readme_agent = ReadmeUpdaterAgent(github_token)
    
    # Create test PR analysis data
    test_pr_analysis = {
        "repository": "bahen4x/test-repo",  # Replace with your test repo
        "pr_number": 1,
        "priority": "high",
        "requires_documentation": True,
        "changes_summary": {
            "files_changed": 3,
            "lines_added": 25,
            "lines_removed": 10
        },
        "suggested_actions": [
            "Update API documentation for new endpoints",
            "Add code examples for new features",
            "Update configuration guide"
        ]
    }
    
    # Create test AI comment
    test_ai_comment = {
        "output": """## 🤖 AI Documentation Analysis

### 📊 Change Summary
This PR introduces significant improvements to the codebase with new API endpoints and enhanced functionality.

### 🔧 Technical Details
- **New Features**: Added user authentication system
- **API Changes**: New /auth endpoints added
- **Configuration**: Updated environment variable handling

### 📚 Documentation Requirements
Based on the analysis, the following documentation updates are recommended:
- Update API reference with new authentication endpoints
- Add authentication flow examples
- Update configuration documentation

### ✨ Key Improvements
- Enhanced security with proper authentication
- Improved error handling and validation
- Better configuration management

This PR represents a significant enhancement to the system's capabilities."""
    }
    
    # Create test webhook payload
    test_webhook_payload = {
        "action": "opened",
        "pull_request": {
            "number": 1,
            "title": "Add authentication system",
            "head": {
                "ref": "feature/auth-system"
            }
        },
        "repository": {
            "full_name": "bahen4x/test-repo"
        }
    }
    
    print("📝 Test Data:")
    print(f"   Repository: {test_pr_analysis['repository']}")
    print(f"   PR Number: {test_pr_analysis['pr_number']}")
    print(f"   Priority: {test_pr_analysis['priority']}")
    print(f"   Branch: {test_webhook_payload['pull_request']['head']['ref']}")
    print()
    
    # Test the README update
    print("🚀 Testing README update...")
    try:
        result = readme_agent.update_readme_with_ai_insights(
            pr_analysis=test_pr_analysis,
            ai_comment=test_ai_comment,
            webhook_payload=test_webhook_payload
        )
        
        print("📊 Result:")
        print(json.dumps(result, indent=2))
        
        if result.get('status') == 'success':
            print()
            print("✅ SUCCESS! README.md updated successfully")
            print(f"   Repository: {result.get('repository')}")
            print(f"   Branch: {result.get('branch')}")
            print(f"   File: {result.get('file')}")
            print(f"   PR: #{result.get('pr_number')}")
        else:
            print()
            print("❌ FAILED! README.md update unsuccessful")
            print(f"   Error: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()