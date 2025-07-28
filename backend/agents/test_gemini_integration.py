#!/usr/bin/env python3
"""
Test script to verify Google Gemini integration works.
"""

import os
import sys
from decouple import Config, RepositoryEnv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_gemini_integration():
    """Test Google Gemini integration with the webhook server."""
    
    print("🧪 Testing Google Gemini Integration")
    print("=" * 50)
    
    # Load environment config
    backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(backend_env_path):
        env_config = Config(RepositoryEnv(backend_env_path))
    else:
        from decouple import config as env_config
    
    google_api_key = env_config('GOOGLE_API_KEY', default='')
    
    if not google_api_key:
        print("❌ GOOGLE_API_KEY not found in environment")
        return False
    
    print(f"🔑 Google API Key: {'✅ Configured' if google_api_key else '❌ Missing'}")
    
    # Test Gemini directly
    try:
        import google.generativeai as genai
        
        print("📦 Google Generative AI library: ✅ Available")
        
        # Configure Gemini
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("🤖 Gemini model: ✅ Initialized")
        
        # Test simple generation
        test_prompt = """You are DocuSync AI. Analyze this test pull request:

Repository: test-repo
PR Number: #1
Changes: Added new user authentication system
Files Changed: 3
Priority: high

Generate a brief technical documentation summary (max 200 words)."""

        print("🔄 Testing content generation...")
        response = model.generate_content(test_prompt)
        
        if response and response.text:
            print("✅ Gemini generation successful!")
            print("\n📄 Sample Response:")
            print("-" * 40)
            print(response.text[:300] + "..." if len(response.text) > 300 else response.text)
            print("-" * 40)
            return True
        else:
            print("❌ Empty response from Gemini")
            return False
            
    except ImportError:
        print("❌ Google Generative AI library not installed")
        print("   Run: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Error testing Gemini: {e}")
        return False

def test_webhook_function():
    """Test the webhook integration function."""
    
    print("\n🔧 Testing Webhook Integration Function")
    print("=" * 50)
    
    # Import the function from webhook server
    try:
        from webhook_server_integrated import generate_ai_documentation_with_gemini
        
        # Create test PR analysis
        test_pr_analysis = {
            "repository": "test-org/test-repo",
            "pr_number": 42,
            "priority": "high",
            "requires_documentation": True,
            "changes_summary": {"files_changed": 5},
            "suggested_actions": [
                "Update API documentation",
                "Add code examples",
                "Update configuration guide"
            ]
        }
        
        test_diff = """diff --git a/src/auth.py b/src/auth.py
new file mode 100644
index 0000000..abcd123
--- /dev/null
+++ b/src/auth.py
@@ -0,0 +1,25 @@
+class AuthSystem:
+    def __init__(self):
+        self.users = {}
+    
+    def authenticate(self, username, password):
+        return username in self.users"""
        
        print("🔄 Testing webhook AI generation function...")
        result = generate_ai_documentation_with_gemini(test_pr_analysis, test_diff)
        
        if result and result.get('output'):
            print("✅ Webhook AI generation successful!")
            print(f"📊 Response length: {len(result['output'])} characters")
            print("\n📄 Sample Output:")
            print("-" * 40)
            print(result['output'][:400] + "..." if len(result['output']) > 400 else result['output'])
            print("-" * 40)
            return True
        else:
            print("❌ No output generated")
            return False
            
    except ImportError as e:
        print(f"❌ Could not import webhook function: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing webhook function: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 DocuSync Gemini Integration Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # Test 1: Direct Gemini integration
    if test_gemini_integration():
        success_count += 1
    
    # Test 2: Webhook function integration
    if test_webhook_function():
        success_count += 1
    
    print("\n🏁 Test Results")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("\n🎉 All tests passed! Gemini integration is working correctly.")
        return True
    else:
        print("\n⚠️  Some tests failed. Check the configuration and try again.")
        return False

if __name__ == "__main__":
    main()