#!/usr/bin/env python3
"""
Main entry point for the DocuSync Commit Watcher Agent.
This script starts the agent and registers it with the Conductor server.
"""

import os
import sys
import logging
import signal
from typing import Optional
from decouple import config, Config, RepositoryEnv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commit_watcher_agent import CommitWatcherAgent
from github_bot_agent import GitHubBotAgent
from simple_workflows import register_simple_workflows, register_dict_workflow
from conductor.client.configuration.configuration import Configuration
from conductor.client.configuration.settings.authentication_settings import AuthenticationSettings
# from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.orkes.orkes_workflow_client import OrkesWorkflowClient


# Load config from backend/.env file
backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(backend_env_path):
    env_config = Config(RepositoryEnv(backend_env_path))
else:
    env_config = config

# Configure logging
logging.basicConfig(
    level=getattr(logging, env_config('LOG_LEVEL', default='INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocuSyncAgentManager:
    """Manager class for the DocuSync agent system."""
    
    def __init__(self):
        self.commit_watcher_agent: Optional[CommitWatcherAgent] = None
        self.github_bot_agent: Optional[GitHubBotAgent] = None
        self.workflow_client: Optional[OrkesWorkflowClient] = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.running = False
        if self.commit_watcher_agent:
            self.commit_watcher_agent.task_handler.stop_processes()
        if self.github_bot_agent:
            self.github_bot_agent.task_handler.stop_processes()
    
    def setup_conductor_client(self) -> bool:
        """Setup Conductor client configuration."""
        try:
            conductor_server = env_config('ORKES_SERVER_URL', default='http://localhost:8080/api')
            conductor_key = env_config('ORKES_API_KEY', default='')
            
            if conductor_key:
                # Use authenticated connection (Orkes Cloud)
                # For Orkes Cloud, the API key is used as both key_id and key_secret
                auth_settings = AuthenticationSettings(key_id=conductor_key, key_secret=conductor_key)
                configuration = Configuration(
                    server_api_url=conductor_server,
                    authentication_settings=auth_settings
                )
                logger.info("Using authenticated Conductor connection (Orkes Cloud)")
            else:
                # Use local/unauthenticated connection
                configuration = Configuration(server_api_url=conductor_server)
                logger.info("Using local Conductor connection")
            
            self.workflow_client = OrkesWorkflowClient(configuration)
            
            # Test connection
            self.workflow_client.get_workflow_client().get_workflow_def('test', 1)
            logger.info("✅ Conductor connection established")
            return True
            
        except Exception as e:
            logger.warning(f"Conductor connection failed: {e}")
            logger.info("Agent will run in standalone mode")
            return False
    
    def register_workflows(self) -> bool:
        """Register workflows with Conductor."""
        if not self.workflow_client:
            logger.warning("No Conductor client available. Skipping workflow registration.")
            return False
        
        try:
            # Register simplified workflows that work with current SDK
            workflow_client = self.workflow_client.get_workflow_client()
            
            # Try dictionary-based registration first
            if register_dict_workflow(workflow_client):
                logger.info("✅ Dictionary-based workflow registered successfully")
            else:
                # Fallback to object-based registration
                register_simple_workflows(workflow_client)
                logger.info("✅ Object-based workflow registered successfully")
            
            return True
        except Exception as e:
            logger.error(f"Failed to register workflows: {e}")
            logger.warning("Continuing without workflow registration - agents will still work")
            return False
    
    def start_agents(self) -> bool:
        """Start both the commit watcher and GitHub bot agents."""
        github_token = env_config('GITHUB_TOKEN', default='')
        if not github_token:
            logger.error("GITHUB_TOKEN environment variable is required")
            return False
        
        conductor_server = env_config('ORKES_SERVER_URL', default='http://localhost:8080/api')
        conductor_key = env_config('ORKES_API_KEY', default='')
        
        try:
            # Initialize commit watcher agent
            self.commit_watcher_agent = CommitWatcherAgent(
                github_token=github_token,
                conductor_server_url=conductor_server,
                conductor_key=conductor_key
            )
            
            # Initialize GitHub bot agent
            self.github_bot_agent = GitHubBotAgent(
                github_token=github_token,
                conductor_server_url=conductor_server,
                conductor_key=conductor_key
            )
            
            logger.info("✅ All agents initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            return False
    
    def run(self):
        """Main run loop."""
        logger.info("🚀 Starting DocuSync Commit Watcher Agent...")
        
        # Setup Conductor connection
        conductor_available = self.setup_conductor_client()
        
        # Register workflows if Conductor is available
        if conductor_available:
            self.register_workflows()
        
        # Start the agents
        if not self.start_agents():
            logger.error("Failed to start agents. Exiting.")
            return False
        
        # Start polling for tasks
        self.running = True
        logger.info("📡 Agents started and polling for tasks...")
        logger.info("📊 Available workflows:")
        logger.info("  - enhanced_pr_documentation_workflow (with Gemini AI)")
        logger.info("  - ai_feedback_enhancement_workflow")
        logger.info("Press Ctrl+C to stop the agents")
        
        try:
            if conductor_available:
                # Start polling from Conductor for both agents
                logger.info("🔄 Starting Commit Watcher Agent polling...")
                self.commit_watcher_agent.start_polling()
                
                logger.info("🤖 Starting GitHub Bot Agent polling...")
                self.github_bot_agent.start_polling()
                
                # Keep the main thread alive
                import time
                while self.running:
                    time.sleep(1)
            else:
                # Run in standalone mode (for testing)
                logger.info("Running in standalone mode - use simple_test.py for testing")
                import time
                while self.running:
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return False
        finally:
            logger.info("🛑 Agent stopped")
        
        return True


def main():
    """Main entry point."""
    
    # Print startup banner
    print("=" * 60)
    print("   DocuSync Commit Watcher Agent")
    print("   AI-powered documentation maintenance")
    print("=" * 60)
    print()
    
    # Check required environment variables
    required_vars = ['GITHUB_TOKEN']
    missing_vars = [var for var in required_vars if not env_config(var, default='')]
    
    if missing_vars:
        logger.error("Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("Please set these variables and restart the agent.")
        return False
    
    # Start the agent manager
    manager = DocuSyncAgentManager()
    success = manager.run()
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)