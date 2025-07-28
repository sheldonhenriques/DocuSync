#!/usr/bin/env python3
"""
GitHub API Test Script for DocuSync
Tests various GitHub API endpoints that will be used in the DocuSync application
"""

import os
import requests
import json
from typing import Dict, List, Optional

class GitHubAPITester:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DocuSync-Test/1.0"
        }
        
    def make_request(self, endpoint: str, method: str = "GET") -> Dict:
        """Make a request to the GitHub API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers)
            print(f"[{method}] {endpoint} -> Status: {response.status_code}")
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False, 
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_authenticated_user(self) -> Dict:
        """Test getting the authenticated user's info"""
        print("\n🔍 Testing authenticated user endpoint...")
        return self.make_request("/user")
    
    def test_user_profile(self, username: str) -> Dict:
        """Test getting a specific user's profile"""
        print(f"\n👤 Testing user profile for: {username}")
        return self.make_request(f"/users/{username}")
    
    def test_user_repositories(self, username: str, per_page: int = 5) -> Dict:
        """Test getting user's repositories"""
        print(f"\n📚 Testing repositories for user: {username}")
        return self.make_request(f"/users/{username}/repos?per_page={per_page}&sort=updated")
    
    def test_repository_details(self, owner: str, repo: str) -> Dict:
        """Test getting specific repository details"""
        print(f"\n📖 Testing repository details for: {owner}/{repo}")
        return self.make_request(f"/repos/{owner}/{repo}")
    
    def test_repository_contents(self, owner: str, repo: str, path: str = "") -> Dict:
        """Test getting repository contents"""
        print(f"\n📁 Testing repository contents for: {owner}/{repo}/{path}")
        endpoint = f"/repos/{owner}/{repo}/contents/{path}" if path else f"/repos/{owner}/{repo}/contents"
        return self.make_request(endpoint)
    
    def test_repository_commits(self, owner: str, repo: str, per_page: int = 3) -> Dict:
        """Test getting repository commits"""
        print(f"\n📝 Testing recent commits for: {owner}/{repo}")
        return self.make_request(f"/repos/{owner}/{repo}/commits?per_page={per_page}")
    
    def test_repository_hooks(self, owner: str, repo: str) -> Dict:
        """Test getting repository webhooks (requires admin access)"""
        print(f"\n🪝 Testing webhooks for: {owner}/{repo}")
        return self.make_request(f"/repos/{owner}/{repo}/hooks")
    
    def test_rate_limit(self) -> Dict:
        """Test rate limit endpoint"""
        print("\n⏱️  Testing rate limit status...")
        return self.make_request("/rate_limit")
    
    def run_comprehensive_test(self, test_username: str = "jbaeee"):
        """Run all tests"""
        print("🚀 Starting GitHub API Comprehensive Test")
        print("=" * 50)
        
        results = {}
        
        # Test 1: Authenticated user
        results["auth_user"] = self.test_authenticated_user()
        
        # Test 2: Target user profile
        results["user_profile"] = self.test_user_profile(test_username)
        
        # Test 3: User repositories
        results["user_repos"] = self.test_user_repositories(test_username)
        
        # If we got repositories, test additional endpoints
        if results["user_repos"]["success"] and results["user_repos"]["data"]:
            repos = results["user_repos"]["data"]
            if repos:
                first_repo = repos[0]
                owner = first_repo["owner"]["login"]
                repo_name = first_repo["name"]
                
                # Test 4: Repository details
                results["repo_details"] = self.test_repository_details(owner, repo_name)
                
                # Test 5: Repository contents
                results["repo_contents"] = self.test_repository_contents(owner, repo_name)
                
                # Test 6: Repository commits
                results["repo_commits"] = self.test_repository_commits(owner, repo_name)
                
                # Test 7: Repository hooks (might fail if no admin access)
                results["repo_hooks"] = self.test_repository_hooks(owner, repo_name)
        
        # Test 8: Rate limit
        results["rate_limit"] = self.test_rate_limit()
        
        # Print summary
        self.print_test_summary(results)
        
        return results
    
    def print_test_summary(self, results: Dict):
        """Print a summary of all test results"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in results.items():
            total_tests += 1
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
            
            if result["success"]:
                passed_tests += 1
                # Print some key info for successful tests
                if test_name == "user_profile" and "data" in result:
                    data = result["data"]
                    print(f"    → User: {data.get('login')} ({data.get('name', 'N/A')})")
                    print(f"    → Public Repos: {data.get('public_repos', 0)}")
                elif test_name == "user_repos" and "data" in result:
                    repos_count = len(result["data"])
                    print(f"    → Found {repos_count} repositories")
                elif test_name == "rate_limit" and "data" in result:
                    data = result["data"]
                    core_limit = data.get("resources", {}).get("core", {})
                    remaining = core_limit.get("remaining", 0)
                    limit = core_limit.get("limit", 0)
                    print(f"    → Rate Limit: {remaining}/{limit} remaining")
            else:
                print(f"    → Error: {result['error']}")
        
        print(f"\n🎯 Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! GitHub API access is fully functional.")
        elif passed_tests >= total_tests * 0.7:
            print("⚠️  Most tests passed. Some endpoints may require additional permissions.")
        else:
            print("❌ Multiple tests failed. Check your GitHub token permissions.")

def main():
    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        print("❌ Error: GITHUB_TOKEN environment variable not found")
        print("Please set your GitHub token:")
        print("export GITHUB_TOKEN=your_token_here")
        return
    
    # Create tester instance
    tester = GitHubAPITester(github_token)
    
    # Run comprehensive test
    test_username = "jbaeee"
    print(f"Testing GitHub API access with target username: {test_username}")
    
    results = tester.run_comprehensive_test(test_username)
    
    # Save results to file for further analysis
    with open("/workspaces/DocuSync/github_api_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Full test results saved to: github_api_test_results.json")

if __name__ == "__main__":
    main()