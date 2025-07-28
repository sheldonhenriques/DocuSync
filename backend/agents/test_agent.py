#!/usr/bin/env python3
"""
Test script for the Commit Watcher Agent.
Tests the agent with sample PR webhook data.
"""

import json
import os
import sys
from datetime import datetime
from decouple import config

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commit_watcher_agent import CommitWatcherAgent
from github_client import GitHubClient


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
            "body": "Adding documentation improvements",
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


def test_github_client():
    """Test the GitHub client functionality."""
    print("Testing GitHub Client...")
    
    github_token = config('GITHUB_TOKEN', default='')
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment")
        return False
    
    client = GitHubClient(github_token)
    
    # Test PR analysis
    try:
        analysis = client.analyze_pr_changes("sheldonhenriques", "DocuSync", 1)
        
        if "error" in analysis:
            print(f"❌ GitHub API Error: {analysis['error']}")
            return False
        
        print("✅ GitHub client working correctly")
        print(f"   - PR Title: {analysis['pr_details']['title']}")
        print(f"   - Files Changed: {analysis['pr_details']['changed_files']}")
        print(f"   - Requires Documentation: {analysis['documentation_impact']['requires_doc_update']}")
        
        return True
        
    except Exception as e:
        print(f"❌ GitHub client test failed: {e}")
        return False


def test_agent_analysis():
    """Test the agent's PR analysis functionality."""
    print("\nTesting Agent PR Analysis...")
    
    github_token = config('GITHUB_TOKEN', default='')
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment")
        return False
    
    # Create agent (without Conductor connection for testing)
    agent = CommitWatcherAgent(github_token)
    
    # Create sample webhook
    webhook_payload = create_sample_pr_webhook()
    
    try:
        # Test the analysis method directly
        result = agent.analyze_pr_webhook(webhook_payload)
        
        if "error" in result:
            print(f"❌ Agent analysis failed: {result['error']}")
            return False
        
        print("✅ Agent analysis working correctly")
        print(f"   - Repository: {result['repository']}")
        print(f"   - PR Number: {result['pr_number']}")
        print(f"   - Requires Documentation: {result['requires_documentation']}")
        print(f"   - Priority: {result['priority']}")
        print(f"   - Confidence Score: {result.get('confidence_score', 'N/A')}")
        
        if result['suggested_actions']:
            print("   - Suggested Actions:")
            for action in result['suggested_actions']:
                print(f"     • {action}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent analysis test failed: {e}")
        print(f"   Exception type: {type(e).__name__}")
        return False


def test_workflow_structure():
    """Test workflow definitions."""
    print("\nTesting Workflow Definitions...")
    
    try:
        from workflows import (
            create_pr_analysis_workflow,
            create_feedback_processing_workflow,
            create_parallel_pr_processing_workflow
        )
        
        # Test workflow creation
        pr_workflow = create_pr_analysis_workflow()
        feedback_workflow = create_feedback_processing_workflow()
        parallel_workflow = create_parallel_pr_processing_workflow()
        
        print("✅ Workflow definitions created successfully")
        print(f"   - PR Analysis Workflow: {pr_workflow.name} v{pr_workflow.version}")
        print(f"   - Feedback Processing Workflow: {feedback_workflow.name} v{feedback_workflow.version}")
        print(f"   - Parallel Processing Workflow: {parallel_workflow.name} v{parallel_workflow.version}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False


def run_full_test():
    """Run all tests."""
    print("=" * 60)
    print("DocuSync Commit Watcher Agent Test Suite")
    print("=" * 60)
    
    tests = [
        test_github_client,
        test_agent_analysis,
        test_workflow_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The agent is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the configuration and dependencies.")
    
    return passed == total


if __name__ == "__main__":
    # Check if environment variables are set
    if not config('GITHUB_TOKEN', default=''):
        print("⚠️  Warning: GITHUB_TOKEN not set. Some tests may fail.")
        print("   Please set your GitHub Personal Access Token in the environment.")
        print()
    
    success = run_full_test()
    sys.exit(0 if success else 1)