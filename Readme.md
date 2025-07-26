# DocuSync - Autonomous Documentation Maintenance System

## Project Overview
Build **DocuSync**, an AI-agent orchestrated system that automatically maintains documentation by watching code changes, updating docs, validating examples, and incorporating reader feedback. Use **Orkes** for multi-agent coordination with enterprise-grade reliability.

## Core Architecture

### Tech Stack
- **Agent Orchestration**: Orkes (Temporal-based SaaS)
- **Backend**: Python FastAPI workers 
- **Database**: Supabase (PostgreSQL + Auth)
- **GitHub Integration**: GitHub App + REST API
- **Frontend**: React + Supabase UI
- **Code Analysis**: AST parsing, Spectral (OpenAPI), Dredd (API testing)
- **Containerization**: Docker for sandbox execution

## Implementation Plan

### Phase 1: Core Infrastructure (Day 1)

#### 1.1 Project Setup
```bash
mkdir docusync
cd docusync
mkdir -p {agents,orkes,github-app,frontend,database}
```

#### 1.2 Supabase Setup
- Initialize Supabase project
- Create tables:
  ```sql
  -- Users (GitHub OAuth)
  CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id INTEGER UNIQUE,
    username TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT NOW()
  );

  -- Repositories being monitored
  CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    github_repo_id INTEGER,
    repo_name TEXT,
    doc_config JSONB, -- which files/patterns to watch
    created_at TIMESTAMP DEFAULT NOW()
  );

  -- Documentation feedback and suggestions
  CREATE TABLE doc_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID REFERENCES repositories(id),
    file_path TEXT,
    section TEXT,
    feedback_text TEXT,
    suggestion TEXT,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    created_at TIMESTAMP DEFAULT NOW()
  );

  -- Workflow execution logs
  CREATE TABLE workflow_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID REFERENCES repositories(id),
    orkes_workflow_id TEXT,
    trigger_event TEXT, -- pr, commit, feedback
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
  );
  ```

#### 1.3 GitHub App Foundation
Create `github-app/app.py`:
```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import hmac
import hashlib
import os
from orkes_client import OrkesClient

app = FastAPI()
orkes_client = OrkesClient(api_key=os.getenv("ORKES_API_KEY"))

@app.post("/webhook")
async def github_webhook(request: Request):
    # Verify GitHub webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    payload = await request.body()
    
    if not verify_signature(payload, signature):
        return {"error": "Invalid signature"}, 401
    
    event_type = request.headers.get("X-GitHub-Event")
    
    if event_type in ["pull_request", "push"]:
        # Trigger Orkes workflow
        workflow_id = await orkes_client.start_workflow(
            "docusync_main_workflow",
            input_data={
                "event_type": event_type,
                "payload": payload.decode()
            }
        )
        return {"workflow_id": workflow_id}

def verify_signature(payload, signature):
    # Implement GitHub webhook signature verification
    pass
```

### Phase 2: Agent Implementation (Day 1-2)

#### 2.1 Commit Watcher Agent
Create `agents/commit_watcher.py`:
```python
from orkes.worker import Worker
import json
import re
from github import Github

class CommitWatcherAgent(Worker):
    def __init__(self):
        super().__init__("commit_watcher_task")
    
    def execute(self, task_data):
        """
        Analyzes commits/PRs to identify documentation-relevant changes
        Returns: List of files that need doc updates
        """
        event_data = json.loads(task_data["payload"])
        
        # Parse changed files
        changed_files = self.extract_changed_files(event_data)
        
        # Identify doc-relevant changes
        doc_relevant_changes = []
        for file_change in changed_files:
            if self.is_doc_relevant(file_change):
                doc_relevant_changes.append({
                    "file_path": file_change["path"],
                    "change_type": file_change["status"],
                    "diff": file_change["patch"],
                    "priority": self.calculate_priority(file_change)
                })
        
        return {
            "relevant_changes": doc_relevant_changes,
            "repo_info": {
                "name": event_data["repository"]["name"],
                "owner": event_data["repository"]["owner"]["login"]
            }
        }
    
    def is_doc_relevant(self, file_change):
        """Check if file change affects documentation"""
        # API files, config changes, public interfaces
        doc_patterns = [
            r".*\.py$",  # Python files
            r".*api.*",  # API-related files
            r".*\.yaml$", r".*\.yml$",  # Config files
            r".*swagger.*", r".*openapi.*"  # API specs
        ]
        
        for pattern in doc_patterns:
            if re.match(pattern, file_change["path"], re.IGNORECASE):
                return True
        return False

# Register with Orkes
worker = CommitWatcherAgent()
```

#### 2.2 Doc Maintainer Agent
Create `agents/doc_maintainer.py`:
```python
from orkes.worker import Worker
import google.generativeai as genai
import os
from pathlib import Path
import json

class DocMaintainerAgent(Worker):
    def __init__(self):
        super().__init__("doc_maintainer_task")
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    def execute(self, task_data):
        """
        Generates or updates documentation based on code changes
        """
        changes = task_data["relevant_changes"]
        repo_info = task_data["repo_info"]
        
        doc_updates = []
        
        for change in changes:
            # Analyze the code change
            analysis = self.analyze_code_change(change)
            
            # Generate documentation update
            doc_update = self.generate_doc_update(change, analysis)
            
            doc_updates.append({
                "target_file": self.determine_target_doc_file(change),
                "update_type": "modify",  # create, modify, delete
                "content": doc_update,
                "confidence": analysis["confidence"]
            })
        
        return {"doc_updates": doc_updates}
    
    def analyze_code_change(self, change):
        """Use Gemini to understand the semantic meaning of code changes"""
        prompt = f"""
        Analyze this code change and determine its impact on documentation:
        
        File: {change['file_path']}
        Change type: {change['change_type']}
        Diff:
        {change['diff']}
        
        Provide your response in this JSON format:
        {{
            "summary": "Brief summary of what changed",
            "api_impact": "How this affects public APIs or interfaces",
            "doc_sections": ["list", "of", "documentation", "sections", "to", "update"],
            "confidence": 0.85,
            "breaking_change": false
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text
            # Clean up response to extract JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            analysis = json.loads(json_str)
            return analysis
            
        except Exception as e:
            # Fallback response
            return {
                "summary": f"Code change detected in {change['file_path']}",
                "api_impact": "Unknown impact - manual review needed",
                "doc_sections": ["general"],
                "confidence": 0.3,
                "breaking_change": False
            }
    
    def generate_doc_update(self, change, analysis):
        """Generate the actual documentation content using Gemini"""
        prompt = f"""
        Generate updated documentation based on this code change analysis:
        
        File changed: {change['file_path']}
        Analysis: {analysis['summary']}
        API Impact: {analysis['api_impact']}
        
        Code diff:
        {change['diff']}
        
        Requirements:
        - Write clear, concise documentation
        - Include practical code examples
        - Use markdown formatting
        - Focus on what developers need to know
        - If this is a breaking change, clearly highlight it
        - Follow standard documentation patterns
        
        Generate the documentation content:
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"# Documentation Update Needed\n\nFile: {change['file_path']}\n\nA change was detected but automatic documentation generation failed. Manual review required.\n\nError: {str(e)}"
    
    def determine_target_doc_file(self, change):
        """Determine which documentation file should be updated"""
        file_path = change['file_path']
        
        # Simple mapping logic - can be made more sophisticated
        if 'api' in file_path.lower():
            return 'docs/api.md'
        elif file_path.endswith('.py'):
            # Convert Python file to corresponding doc file
            doc_path = file_path.replace('.py', '.md').replace('src/', 'docs/')
            return doc_path
        elif 'config' in file_path.lower():
            return 'docs/configuration.md'
        else:
            return 'docs/README.md'

worker = DocMaintainerAgent()
```

#### 2.3 Style Checker Agent
Create `agents/style_checker.py`:
```python
from orkes.worker import Worker
import re

class StyleCheckerAgent(Worker):
    def __init__(self):
        super().__init__("style_checker_task")
    
    def execute(self, task_data):
        """
        Enforces documentation style and consistency
        """
        doc_updates = task_data["doc_updates"]
        
        styled_updates = []
        for update in doc_updates:
            styled_content = self.apply_style_rules(update["content"])
            styled_updates.append({
                **update,
                "content": styled_content,
                "style_fixes": self.get_style_fixes(update["content"], styled_content)
            })
        
        return {"styled_updates": styled_updates}
    
    def apply_style_rules(self, content):
        """Apply company-specific style rules"""
        # Example rules
        fixes = [
            (r"\bapi\b", "API"),  # Capitalize API
            (r"e\.g\.", "for example"),  # Expand abbreviations
            (r"i\.e\.", "that is"),
        ]
        
        styled = content
        for pattern, replacement in fixes:
            styled = re.sub(pattern, replacement, styled, flags=re.IGNORECASE)
        
        return styled

worker = StyleCheckerAgent()
```

#### 2.4 Validator Agent
Create `agents/validator.py`:
```python
from orkes.worker import Worker
import subprocess
import tempfile
import json

class ValidatorAgent(Worker):
    def __init__(self):
        super().__init__("validator_task")
    
    def execute(self, task_data):
        """
        Validates code examples and API specifications
        """
        styled_updates = task_data["styled_updates"]
        
        validation_results = []
        for update in styled_updates:
            result = self.validate_documentation(update)
            validation_results.append({
                **update,
                "validation": result
            })
        
        return {"validated_updates": validation_results}
    
    def validate_documentation(self, doc_update):
        """Run various validation checks"""
        validations = {
            "code_examples": self.validate_code_examples(doc_update["content"]),
            "links": self.validate_links(doc_update["content"]),
            "formatting": self.validate_formatting(doc_update["content"])
        }
        
        overall_valid = all(v["valid"] for v in validations.values())
        
        return {
            "valid": overall_valid,
            "checks": validations
        }
    
    def validate_code_examples(self, content):
        """Extract and test code examples"""
        # Extract code blocks
        code_blocks = re.findall(r"```python\n(.*?)\n```", content, re.DOTALL)
        
        validation_results = []
        for i, code in enumerate(code_blocks):
            try:
                # Run code in isolated environment
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                    f.flush()
                    
                    result = subprocess.run(
                        ['python', f.name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    validation_results.append({
                        "block_index": i,
                        "valid": result.returncode == 0,
                        "error": result.stderr if result.returncode != 0 else None
                    })
            except Exception as e:
                validation_results.append({
                    "block_index": i,
                    "valid": False,
                    "error": str(e)
                })
        
        return {
            "valid": all(r["valid"] for r in validation_results),
            "results": validation_results
        }

#### 2.5 GitHub Bot Agent
Create `agents/github_bot.py`:
```python
from orkes.worker import Worker
import google.generativeai as genai
import os
from github import Github
import json

class GitHubBotAgent(Worker):
    def __init__(self):
        super().__init__("github_bot_task")
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.github = Github(os.getenv("GITHUB_TOKEN"))
    
    def execute(self, task_data):
        """
        Posts documentation update previews as GitHub comments
        """
        validated_updates = task_data["validated_updates"]
        repo_info = task_data.get("repo_info", {})
        
        # Generate comment summary
        comment_body = self.generate_comment_body(validated_updates)
        
        # Post comment (if this is a PR)
        pr_number = task_data.get("pr_number")
        if pr_number:
            self.post_pr_comment(repo_info, pr_number, comment_body)
        
        return {
            "comment_posted": bool(pr_number),
            "updates_count": len(validated_updates),
            "valid_updates": sum(1 for u in validated_updates if u["validation"]["valid"])
        }
    
    def generate_comment_body(self, validated_updates):
        """Use Gemini to generate a friendly PR comment"""
        updates_summary = []
        for update in validated_updates:
            status = "✅" if update["validation"]["valid"] else "❌"
            updates_summary.append({
                "file": update["target_file"],
                "status": status,
                "valid": update["validation"]["valid"]
            })
        
        prompt = f"""
        Generate a friendly GitHub PR comment for an automated documentation update.
        
        Updates processed: {json.dumps(updates_summary, indent=2)}
        
        Requirements:
        - Professional but friendly tone
        - Summarize what documentation was updated
        - Highlight any validation issues
        - Include a call-to-action for review
        - Use appropriate GitHub markdown and emojis
        - Keep it concise but informative
        
        Generate the comment:
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Fallback comment
            valid_count = sum(1 for u in validated_updates if u["validation"]["valid"])
            total_count = len(validated_updates)
            
            return f"""## 🤖 DocuSync Update
            
**{valid_count}/{total_count}** documentation updates processed successfully.

📝 **Files updated:**
{chr(10).join(f"- {u['target_file']} {'✅' if u['validation']['valid'] else '❌'}" for u in validated_updates)}

Please review the documentation changes in your DocuSync dashboard.
            """
    
    def post_pr_comment(self, repo_info, pr_number, comment_body):
        """Post comment to GitHub PR"""
        try:
            repo_name = f"{repo_info['owner']}/{repo_info['name']}"
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(comment_body)
        except Exception as e:
            print(f"Failed to post GitHub comment: {e}")

#### 2.6 Feedback Agent
Create `agents/feedback_agent.py`:
```python
from orkes.worker import Worker
import google.generativeai as genai
import os
from supabase import create_client, Client

class FeedbackAgent(Worker):
    def __init__(self):
        super().__init__("feedback_agent_task")
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Supabase client for storing feedback
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def execute(self, task_data):
        """
        Processes reader feedback and generates documentation improvements
        """
        feedback_text = task_data["feedback_text"]
        file_path = task_data["file_path"]
        section = task_data.get("section", "")
        current_content = task_data.get("current_content", "")
        
        # Generate improvement suggestion
        suggestion = self.generate_improvement_suggestion(
            feedback_text, file_path, section, current_content
        )
        
        # Store in database for human review
        feedback_record = self.supabase.table('doc_feedback').insert({
            'repo_id': task_data.get("repo_id"),
            'file_path': file_path,
            'section': section,
            'feedback_text': feedback_text,
            'suggestion': suggestion,
            'status': 'pending'
        }).execute()
        
        return {
            "feedback_id": feedback_record.data[0]["id"],
            "suggestion_generated": True,
            "requires_human_review": True
        }
    
    def generate_improvement_suggestion(self, feedback, file_path, section, current_content):
        """Use Gemini to generate documentation improvements based on user feedback"""
        prompt = f"""
        A user provided feedback about unclear documentation. Generate an improved version.
        
        **File:** {file_path}
        **Section:** {section}
        **User Feedback:** "{feedback}"
        
        **Current Content:**
        {current_content}
        
        Requirements:
        - Address the specific confusion mentioned in the feedback
        - Keep the same technical accuracy
        - Make the explanation clearer and more accessible
        - Add examples if they would help
        - Use markdown formatting
        - If the feedback is vague, make reasonable improvements
        
        Generate the improved documentation:
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"**Improvement needed based on user feedback:**\n\nUser said: \"{feedback}\"\n\nCurrent content needs manual review and improvement.\n\nError generating automatic suggestion: {str(e)}"

worker = FeedbackAgent()
```

### Phase 3: Orkes Workflow Definition (Day 2)

#### 3.1 Main Workflow
Create `orkes/workflows.py`:
```python
from orkes.workflow import Workflow, TaskType

def create_docusync_workflow():
    """Define the main DocuSync workflow"""
    workflow = Workflow(name="docusync_main_workflow", version=1)
    
    # Step 1: Watch commits
    commit_watcher = workflow.add_task(
        task_reference_name="watch_commits",
        task_type="commit_watcher_task"
    )
    
    # Step 2: Maintain docs (depends on commit watcher)
    doc_maintainer = workflow.add_task(
        task_reference_name="maintain_docs",
        task_type="doc_maintainer_task",
        task_input={"relevant_changes": "${watch_commits.output.relevant_changes}"}
    )
    
    # Step 3: Style check (depends on doc maintainer)
    style_checker = workflow.add_task(
        task_reference_name="check_style",
        task_type="style_checker_task",
        task_input={"doc_updates": "${maintain_docs.output.doc_updates}"}
    )
    
    # Step 4: Validate (depends on style checker)
    validator = workflow.add_task(
        task_reference_name="validate",
        task_type="validator_task",
        task_input={"styled_updates": "${check_style.output.styled_updates}"}
    )
    
    # Step 5: GitHub bot (depends on validator)
    github_bot = workflow.add_task(
        task_reference_name="github_comment",
        task_type="github_bot_task",
        task_input={"validated_updates": "${validate.output.validated_updates}"}
    )
    
    return workflow

# Register workflow with Orkes
workflow = create_docusync_workflow()
```

### Phase 4: Frontend Dashboard (Day 2-3)

#### 4.1 React Setup
```bash
cd frontend
npx create-react-app docusync-dashboard
cd docusync-dashboard
npm install @supabase/supabase-js @supabase/auth-ui-react
```

#### 4.2 Main Dashboard Component
Create `frontend/src/components/Dashboard.js`:
```jsx
import React, { useState, useEffect } from 'react';
import { supabase } from '../supabaseClient';

function Dashboard() {
  const [repositories, setRepositories] = useState([]);
  const [feedbackItems, setFeedbackItems] = useState([]);
  const [workflowLogs, setWorkflowLogs] = useState([]);

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (user) {
      // Fetch user's repositories
      const { data: repos } = await supabase
        .from('repositories')
        .select('*')
        .eq('user_id', user.id);
      
      setRepositories(repos || []);

      // Fetch pending feedback
      const { data: feedback } = await supabase
        .from('doc_feedback')
        .select('*')
        .eq('status', 'pending');
      
      setFeedbackItems(feedback || []);

      // Fetch recent workflow logs
      const { data: logs } = await supabase
        .from('workflow_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(10);
      
      setWorkflowLogs(logs || []);
    }
  };

  const approveFeedback = async (feedbackId) => {
    await supabase
      .from('doc_feedback')
      .update({ status: 'approved' })
      .eq('id', feedbackId);
    
    fetchUserData(); // Refresh
  };

  return (
    <div className="dashboard">
      <h1>DocuSync Dashboard</h1>
      
      <section className="repositories">
        <h2>Monitored Repositories</h2>
        {repositories.map(repo => (
          <div key={repo.id} className="repo-card">
            <h3>{repo.repo_name}</h3>
            <p>Last updated: {new Date(repo.created_at).toLocaleDateString()}</p>
          </div>
        ))}
      </section>

      <section className="pending-feedback">
        <h2>Pending Documentation Updates</h2>
        {feedbackItems.map(item => (
          <div key={item.id} className="feedback-card">
            <h4>{item.file_path}</h4>
            <p><strong>Issue:</strong> {item.feedback_text}</p>
            <p><strong>Suggested Fix:</strong> {item.suggestion}</p>
            <div className="actions">
              <button onClick={() => approveFeedback(item.id)}>
                Approve
              </button>
              <button onClick={() => rejectFeedback(item.id)}>
                Reject
              </button>
            </div>
          </div>
        ))}
      </section>

      <section className="workflow-logs">
        <h2>Recent Activity</h2>
        {workflowLogs.map(log => (
          <div key={log.id} className="log-item">
            <span className={`status ${log.status}`}>{log.status}</span>
            <span>{log.trigger_event}</span>
            <span>{new Date(log.created_at).toLocaleString()}</span>
          </div>
        ))}
      </section>
    </div>
  );
}

export default Dashboard;
```

### Phase 5: Integration & Demo (Day 3)

#### 5.1 Docker Compose Setup
Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  github-app:
    build: ./github-app
    ports:
      - "8000:8000"
    environment:
      - ORKES_API_KEY=${ORKES_API_KEY}
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}

  commit-watcher:
    build: ./agents
    command: python commit_watcher.py
    environment:
      - ORKES_API_KEY=${ORKES_API_KEY}

  doc-maintainer:
    build: ./agents
    command: python doc_maintainer.py
    environment:
      - ORKES_API_KEY=${ORKES_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}

  style-checker:
    build: ./agents
    command: python style_checker.py
    environment:
      - ORKES_API_KEY=${ORKES_API_KEY}

  validator:
    build: ./agents
    command: python validator.py
    environment:
      - ORKES_API_KEY=${ORKES_API_KEY}
      - DAYTONA_API_KEY=${DAYTONA_API_KEY}
      - DAYTONA_BASE_URL=${DAYTONA_BASE_URL}

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_SUPABASE_URL=${SUPABASE_URL}
      - REACT_APP_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
```

#### 5.2 Demo Script & Test Data
Create realistic demo scenarios:
1. **PR with API change** → shows automatic doc updates
2. **Reader feedback** → shows agent response loop
3. **Breaking change detection** → shows validation preventing issues

## Key Implementation Notes

### Environment Variables Needed
```bash
# Orkes
ORKES_API_KEY=your_orkes_api_key
ORKES_SERVER_URL=https://play.orkes.io/api

# Supabase  
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# GitHub
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY=your_private_key
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Google Gemini
GOOGLE_API_KEY=your_google_api_key

# Daytona SDK
DAYTONA_API_KEY=your_daytona_api_key
DAYTONA_BASE_URL=https://api.daytona.io
DAYTONA_CLEANUP=true  # Set to false to keep workspaces for debugging
```

### Orkes Setup Steps
1. Sign up at [Orkes Cloud](https://orkes.io)
2. Create new application
3. Register your workflow definition
4. Deploy workers to Orkes (they provide SDKs)

### GitHub App Setup
1. Create GitHub App in your GitHub settings
2. Set webhook URL to your deployed GitHub app endpoint
3. Request permissions: Contents, Pull requests, Issues
4. Generate private key for authentication

## Success Metrics for Demo
- **Response time**: PR → doc update suggestions in <2 minutes
- **Accuracy**: Code examples that actually run
- **User experience**: Clean dashboard showing agent coordination
- **Enterprise features**: Approval workflows, audit logs via Orkes

This creates a production-ready system that demonstrates sophisticated multi-agent coordination while solving a real enterprise problem. The Orkes integration provides the reliability and observability that enterprise customers demand.