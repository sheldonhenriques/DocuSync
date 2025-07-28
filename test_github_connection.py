#!/usr/bin/env python3

import os
import sys
from github import Github

# Test GitHub connection using the token from .env
def test_github_connection():
    # Load the token from backend .env
    token = <YOUR_GITHUB_PAT_HERE>
    
    print(f"Testing GitHub connection with token: {token[:20]}...")
    
    try:
        # Create GitHub client
        g = Github(token)
        
        # Test with user info
        user = g.get_user()
        print(f"Authenticated as: {user.login}")
        print(f"User name: {user.name}")
        
        # Test with a simple public repository
        try:
            repo = g.get_repo("octocat/Hello-World")
            print(f"Successfully accessed repository: {repo.full_name}")
            print(f"Repository description: {repo.description}")
            print(f"Repository stars: {repo.stargazers_count}")
        except Exception as e:
            print(f"Error accessing repository: {e}")
            
        # Test rate limits
        rate_limit = g.get_rate_limit()
        print(f"Rate limit remaining: {rate_limit.core.remaining}/{rate_limit.core.limit}")
        
    except Exception as e:
        print(f"GitHub connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_github_connection()
    sys.exit(0 if success else 1)