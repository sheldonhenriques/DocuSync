#!/usr/bin/env python3
"""
Simple test script for testing agent functionality without Conductor.
"""

import json
import os
import sys
from datetime import datetime
from decouple import config, Config, RepositoryEnv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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


def analyze_pr_webhook_simple(webhook_payload, github_client):
    """Simplified version of PR webhook analysis without Conductor decorators."""
    
    try:
        print(f"Processing PR webhook: {webhook_payload.get('action', 'unknown')}")
        
        # Extract PR information from webhook
        pr_info = extract_pr_info_from_webhook(webhook_payload)
        if not pr_info:
            return {"error": "Invalid webhook payload", "requires_documentation": False}
        
        print(f"Analyzing PR #{pr_info['pr_number']} in {pr_info['owner']}/{pr_info['repo']}")
        
        # Get detailed PR analysis
        pr_analysis = github_client.analyze_pr_changes(
            owner=pr_info["owner"],
            repo=pr_info["repo"],
            pr_number=pr_info["pr_number"]
        )
        
        if "error" in pr_analysis:
            return {"error": pr_analysis["error"], "requires_documentation": False}
        
        # Determine documentation requirements
        doc_requirements = determine_documentation_requirements(pr_analysis)
        
        # Calculate priority level
        priority = calculate_priority(pr_analysis, doc_requirements)
        
        result = {
            "webhook_action": webhook_payload.get("action"),
            "repository": f"{pr_info['owner']}/{pr_info['repo']}",
            "pr_number": pr_info["pr_number"],
            "pr_title": pr_analysis["pr_details"]["title"],
            "pr_author": pr_analysis["pr_details"]["author"],
            "changes_summary": {
                "files_changed": pr_analysis["pr_details"]["changed_files"],
                "additions": pr_analysis["pr_details"]["additions"],
                "deletions": pr_analysis["pr_details"]["deletions"],
                "file_types": pr_analysis["file_analysis"]["file_types"]
            },
            "documentation_requirements": doc_requirements,
            "priority": priority,
            "requires_documentation": doc_requirements["requires_update"],
            "diff_preview": pr_analysis["diff"][:500] if pr_analysis["diff"] else None,
            "files_requiring_docs": identify_files_requiring_docs(pr_analysis["files"]),
            "suggested_actions": doc_requirements["suggested_actions"],
            "confidence_score": doc_requirements["confidence_score"]
        }
        
        print(f"PR analysis completed. Requires docs: {result['requires_documentation']}")
        return result
        
    except Exception as e:
        print(f"Error analyzing PR webhook: {e}")
        return {
            "error": str(e),
            "requires_documentation": False,
            "webhook_action": webhook_payload.get("action", "unknown")
        }


def extract_pr_info_from_webhook(webhook_payload):
    """Extract PR information from GitHub webhook payload."""
    try:
        pr = webhook_payload.get("pull_request", {})
        repo = webhook_payload.get("repository", {})
        
        return {
            "owner": repo.get("owner", {}).get("login"),
            "repo": repo.get("name"),
            "pr_number": pr.get("number"),
            "action": webhook_payload.get("action")
        }
    except Exception as e:
        print(f"Error extracting PR info from webhook: {e}")
        return None


def determine_documentation_requirements(pr_analysis):
    """Determine if and what kind of documentation updates are required."""
    doc_impact = pr_analysis.get("documentation_impact", {})
    file_analysis = pr_analysis.get("file_analysis", {})
    
    requires_update = doc_impact.get("requires_doc_update", False)
    confidence_score = 0.5  # Base confidence
    
    suggested_actions = []
    
    # Check for API changes
    if any(f.endswith(('.py', '.js', '.ts', '.java')) for f in file_analysis.get("code_files", [])):
        confidence_score += 0.3
        suggested_actions.append("Review code changes for API documentation updates")
    
    # Check for configuration changes
    if file_analysis.get("config_files"):
        confidence_score += 0.2
        suggested_actions.append("Update configuration documentation")
    
    # Existing documentation changes
    if file_analysis.get("documentation_files"):
        confidence_score += 0.1
        suggested_actions.append("Review documentation changes for consistency")
    
    return {
        "requires_update": requires_update or confidence_score > 0.6,
        "confidence_score": min(confidence_score, 1.0),
        "impact_level": doc_impact.get("impact_level", "low"),
        "reasons": doc_impact.get("reasons", []),
        "suggested_actions": suggested_actions or doc_impact.get("suggested_actions", [])
    }


def calculate_priority(pr_analysis, doc_requirements):
    """Calculate overall priority for documentation updates."""
    if not doc_requirements.get("requires_update", False):
        return "none"
    
    impact_level = doc_requirements.get("impact_level", "low")
    confidence = doc_requirements.get("confidence_score", 0.0)
    
    if impact_level == "high" and confidence > 0.8:
        return "critical"
    elif impact_level == "high" or confidence > 0.7:
        return "high"
    elif impact_level == "medium" or confidence > 0.5:
        return "medium"
    else:
        return "low"


def identify_files_requiring_docs(files):
    """Identify specific files that likely require documentation updates."""
    doc_files = []
    
    for file in files:
        filename = file.get("filename", "")
        patch = file.get("patch", "")
        
        # Check for API-related files
        if is_api_file(filename, patch):
            doc_files.append(filename)
        # Check for public interface changes
        elif "public" in patch.lower() or "export" in patch.lower():
            doc_files.append(filename)
    
    return doc_files


def is_api_file(filename, patch):
    """Determine if a file contains API definitions."""
    api_indicators = [
        "api", "endpoint", "route", "controller", "service",
        "def ", "function ", "class ", "interface ", "@app.route",
        "router.", "express.", "fastapi"
    ]
    
    return (
        any(indicator in filename.lower() for indicator in api_indicators[:5]) or
        any(indicator in patch.lower() for indicator in api_indicators[5:])
    )


def main():
    """Run the simple test."""
    print("=" * 60)
    print("DocuSync Agent - Simple Test")
    print("=" * 60)
    
    # Load config from backend/.env file
    backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(backend_env_path):
        env_config = Config(RepositoryEnv(backend_env_path))
        print(f"✅ Loaded configuration from {backend_env_path}")
    else:
        env_config = config
        print("⚠️  Using system environment variables")
    
    # Test GitHub client
    github_token = env_config('GITHUB_TOKEN', default='')
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment")
        return False
    
    client = GitHubClient(github_token)
    webhook_payload = create_sample_pr_webhook()
    
    # Run the analysis
    result = analyze_pr_webhook_simple(webhook_payload, client)
    
    # Display results
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False
    
    print(f"Repository: {result['repository']}")
    print(f"PR #{result['pr_number']}: {result['pr_title']}")
    print(f"Author: {result['pr_author']}")
    print(f"Action: {result['webhook_action']}")
    
    print(f"\nChanges Summary:")
    changes = result['changes_summary']
    print(f"  - Files Changed: {changes['files_changed']}")
    print(f"  - Additions: {changes['additions']}")
    print(f"  - Deletions: {changes['deletions']}")
    print(f"  - File Types: {changes['file_types']}")
    
    print(f"\nDocumentation Analysis:")
    print(f"  - Requires Documentation: {result['requires_documentation']}")
    print(f"  - Priority: {result['priority']}")
    print(f"  - Confidence Score: {result['confidence_score']:.2f}")
    
    if result['suggested_actions']:
        print(f"\nSuggested Actions:")
        for action in result['suggested_actions']:
            print(f"  • {action}")
    
    if result['files_requiring_docs']:
        print(f"\nFiles Requiring Documentation:")
        for file in result['files_requiring_docs']:
            print(f"  • {file}")
    
    if result['diff_preview']:
        print(f"\nDiff Preview (first 500 chars):")
        print("-" * 40)
        print(result['diff_preview'])
        print("-" * 40)
    
    print("\n✅ Test completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)