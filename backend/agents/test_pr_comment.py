#!/usr/bin/env python3
"""
Test script to actually post a comment on the GitHub PR using the bot agent.
This demonstrates the complete flow from LLM response to GitHub comment.
"""

import json
import os
import sys
from datetime import datetime
from decouple import Config, RepositoryEnv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from github_bot_agent import GitHubBotAgent
from commit_watcher_agent import CommitWatcherAgent


def create_sample_pr_webhook():
    """Create a sample PR webhook payload for testing."""
    return {
        "action": "opened",
        "number": 1,
        "pull_request": {
            "url": "https://api.github.com/repos/sheldonhenriques/DocuSync/pulls/1",
            "id": 2697555551,
            "number": 1,
            "state": "open",
            "title": "Update Readme.md",
            "user": {
                "login": "sheldonhenriques",
                "id": 32040506
            },
            "body": "Adding documentation improvements and new features",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "head": {
                "ref": "test",
                "sha": "156e823bb31fe10c102f9a3365c19e2cb3dddd21"
            },
            "base": {
                "ref": "main",
                "sha": "b63f1e9f1d8aec036e842c602a99f534dec9e185"
            },
            "additions": 2,
            "deletions": 0,
            "changed_files": 1
        },
        "repository": {
            "id": 1026822051,
            "name": "DocuSync",
            "full_name": "sheldonhenriques/DocuSync",
            "owner": {
                "login": "sheldonhenriques",
                "id": 32040506
            }
        },
        "sender": {
            "login": "sheldonhenriques",
            "id": 32040506
        }
    }


def create_mock_llm_response():
    """Create a mock LLM response that simulates what Gemini would return."""
    return {
        "output": """## 🤖 DocuSync AI Review

### 📊 Change Analysis
This PR adds a simple line to the README file with the text `#added this line`. The change is minimal and appears to be for testing purposes. It's a straightforward documentation update with no functional impact on the codebase.

**Change Type**: Documentation Update  
**Impact**: Low - only affects README content  
**Risk**: Minimal - no code functionality affected  
**Files Modified**: 1 (README.md)

### 📚 Documentation Assessment
✅ **No additional documentation required**

This change is self-contained within the README file. The modification is simple and doesn't introduce new features, APIs, or configuration changes that would require additional documentation updates.

### 🔍 Technical Details
- **Lines Added**: 2
- **Lines Deleted**: 0  
- **File Type**: Markdown documentation
- **Breaking Changes**: None
- **Dependencies**: No impact

### 🎯 Recommendations
1. **Review for clarity** - Ensure the added content aligns with documentation standards
2. **Consider context** - If this is not just a test, consider adding more descriptive content
3. **Ready to merge** - This is a low-risk documentation improvement

### ✨ Next Steps
This PR is ready for review and can be merged once approved. The change poses no risk to the codebase functionality.

Great work on keeping the documentation updated! 🚀"""
    }


def test_pr_comment_posting():
    """Test posting an actual comment to the GitHub PR."""
    
    print("=" * 80)
    print("🚀 Testing GitHub PR Comment Posting with LLM Output")
    print("=" * 80)
    
    # Load config from backend/.env file
    backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(backend_env_path):
        env_config = Config(RepositoryEnv(backend_env_path))
        print(f"✅ Loaded configuration from {backend_env_path}")
    else:
        from decouple import config as env_config
        print("⚠️  Using system environment variables")
    
    # Check GitHub token
    github_token = env_config('GITHUB_TOKEN', default='')
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment")
        return False
    
    print(f"✅ GitHub token configured (length: {len(github_token)})")
    print()
    
    # Step 1: Get PR analysis
    print("🔍 Step 1: Analyzing PR...")
    webhook_payload = create_sample_pr_webhook()
    
    # Create commit watcher agent to analyze the PR
    commit_agent = CommitWatcherAgent(github_token)
    pr_analysis = commit_agent.analyze_pr_webhook(webhook_payload)
    
    print(f"   Repository: {pr_analysis['repository']}")
    print(f"   PR #{pr_analysis['pr_number']}: {pr_analysis['pr_title']}")
    print(f"   Author: {pr_analysis['pr_author']}")
    print(f"   Requires Documentation: {pr_analysis['requires_documentation']}")
    print(f"   Priority: {pr_analysis['priority']}")
    print()
    
    # Step 2: Create mock LLM response
    print("🤖 Step 2: Preparing AI-generated comment...")
    ai_comment = create_mock_llm_response()
    print(f"   Comment length: {len(ai_comment['output'])} characters")
    print("   Preview:", ai_comment['output'][:100] + "...")
    print()
    
    # Step 3: Create GitHub bot agent
    print("📝 Step 3: Initializing GitHub Bot Agent...")
    try:
        bot_agent = GitHubBotAgent(github_token)
        print("   ✅ GitHub Bot Agent initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize GitHub Bot Agent: {e}")
        return False
    print()
    
    # Step 4: Post the comment
    print("💬 Step 4: Posting comment to GitHub PR...")
    print("   This will post a real comment to your PR!")
    
    # Ask for confirmation before posting
    confirmation = input("   Do you want to proceed? (y/N): ").strip().lower()
    if confirmation not in ['y', 'yes']:
        print("   ⏹️  Comment posting cancelled by user")
        return True
    
    try:
        result = bot_agent.post_github_comment(
            pr_analysis=pr_analysis,
            ai_comment=ai_comment
        )
        
        if result.get('status') == 'success':
            print("   ✅ Comment posted successfully!")
            print(f"   📍 Posted to: {pr_analysis['repository']}#{pr_analysis['pr_number']}")
            print(f"   📊 Comment length: {result.get('comment_length', 'unknown')} characters")
        else:
            print(f"   ❌ Failed to post comment: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception while posting comment: {e}")
        return False
    
    print()
    
    # Step 5: Summary
    print("=" * 80)
    print("✅ Test Completed Successfully!")
    print("=" * 80)
    
    print("🎯 **What was tested:**")
    print("   • GitHub PR webhook analysis")
    print("   • LLM response simulation (Gemini output format)")
    print("   • GitHub Bot Agent initialization")
    print("   • Real GitHub API comment posting")
    print("   • Error handling and logging")
    print()
    
    print("🔗 **Check the result:**")
    print(f"   Visit: https://github.com/{pr_analysis['repository']}/pull/{pr_analysis['pr_number']}")
    print("   You should see the AI-generated comment posted by DocuSync Bot")
    print()
    
    print("🚀 **Production workflow:**")
    print("   1. Orkes receives GitHub webhook")
    print("   2. Commit Watcher Agent analyzes changes")
    print("   3. Orkes LLM task calls Gemini for comment generation")
    print("   4. GitHub Bot Agent posts the AI comment")
    print("   5. Developers see intelligent analysis on their PRs")
    print()
    
    return True


if __name__ == "__main__":
    success = test_pr_comment_posting()
    sys.exit(0 if success else 1)