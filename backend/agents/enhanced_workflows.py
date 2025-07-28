from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.simple_task import SimpleTask
from conductor.client.workflow.task.switch_task import SwitchTask
from conductor.client.workflow.task.fork_join_task import ForkJoinTask
from conductor.client.workflow.task.llm_tasks.llm_generate_task import LlmGenerateTask


def create_enhanced_pr_documentation_workflow() -> ConductorWorkflow:
    """
    Enhanced PR documentation workflow that uses Orkes LLM tasks to call Gemini
    for generating AI-powered documentation summaries and suggestions.
    """
    
    workflow = ConductorWorkflow(
        name='enhanced_pr_documentation_workflow',
        version=1,
        description='AI-powered PR analysis with Gemini-generated documentation'
    )
    
    # Task 1: Analyze PR webhook payload
    analyze_pr_task = SimpleTask(
        task_def_name='analyze_pr_webhook',
        task_reference_name='analyze_pr_webhook_ref',
        inputs={
            'webhook_payload': '${workflow.input.webhook_payload}'
        }
    )
    
    # Task 2: Generate AI summary of changes using Gemini
    generate_ai_summary_task = LlmGenerateTask(
        task_reference_name='generate_ai_summary_ref',
        llm_provider='google_vertex_ai',  # Orkes supports Gemini via Vertex AI
        model='gemini-pro',
        prompt='''You are an expert code reviewer and technical writer. Analyze the following GitHub PR changes and provide a comprehensive summary.

PR Details:
- Repository: ${analyze_pr_webhook_ref.output.repository}
- Title: ${analyze_pr_webhook_ref.output.pr_title}
- Author: ${analyze_pr_webhook_ref.output.pr_author}
- Files Changed: ${analyze_pr_webhook_ref.output.changes_summary.files_changed}
- Lines Added: ${analyze_pr_webhook_ref.output.changes_summary.additions}
- Lines Deleted: ${analyze_pr_webhook_ref.output.changes_summary.deletions}

Code Diff:
${analyze_pr_webhook_ref.output.diff_preview}

Provide a structured analysis in this format:

## 🔍 Change Summary
Brief overview of what was modified (2-3 sentences)

## 🎯 Change Type
- [ ] Feature Addition
- [ ] Bug Fix  
- [ ] Refactoring
- [ ] Documentation Update
- [ ] Configuration Change
- [ ] Other: ___

## 💡 Technical Impact
- What components/modules are affected
- Potential impact on existing functionality
- Any notable patterns or approaches used

## ⚠️ Attention Points
- Breaking changes (if any)
- Dependencies affected
- Areas requiring careful review

Keep the response concise but informative (max 300 words).''',
        instructions='Analyze the PR changes and provide a comprehensive technical summary for developers and reviewers.',
        temperature=0.3,
        top_p=0.8,
        max_tokens=800
    )
    
    # Task 3: Extract and categorize PR changes
    extract_changes_task = SimpleTask(
        task_def_name='extract_pr_changes',
        task_reference_name='extract_pr_changes_ref',
        inputs={
            'pr_data': '${analyze_pr_webhook_ref.output}'
        }
    )
    
    # Task 4: Assess documentation priority
    assess_priority_task = SimpleTask(
        task_def_name='assess_documentation_priority',
        task_reference_name='assess_priority_ref',
        inputs={
            'changes_data': '${extract_pr_changes_ref.output}'
        }
    )
    
    # Decision: Should we generate documentation?
    documentation_switch = SwitchTask(
        task_reference_name='documentation_required_switch',
        case_expression='${analyze_pr_webhook_ref.output.requires_documentation}',
        use_javascript=False
    )
    
    # Task 5a: Generate comprehensive documentation using Gemini (if required)
    generate_documentation_task = LlmGenerateTask(
        task_reference_name='generate_documentation_ref',
        llm_provider='google_vertex_ai',
        model='gemini-pro',
        prompt='''You are a technical documentation specialist. Based on the PR analysis and code changes, generate comprehensive documentation updates.

PR Information:
- Repository: ${analyze_pr_webhook_ref.output.repository}
- Title: ${analyze_pr_webhook_ref.output.pr_title}
- Priority: ${assess_priority_ref.output.priority}
- Change Type: Based on analysis

Code Changes:
${analyze_pr_webhook_ref.output.diff_preview}

AI Analysis:
${generate_ai_summary_ref.output}

Please generate documentation in the following sections:

## 📋 Documentation Requirements

### 1. README Updates
- What sections of README need updates?
- New installation/usage instructions needed?

### 2. API Documentation  
- New endpoints/functions to document?
- Changed function signatures?
- Updated examples needed?

### 3. Code Examples
- Provide updated code examples if applicable
- Include before/after examples for breaking changes

### 4. Configuration Changes
- New configuration options?
- Updated environment variables?
- Migration guide needed?

### 5. Testing Documentation
- New test cases to document?
- Updated testing procedures?

### 6. Deployment Notes
- Any deployment considerations?
- Infrastructure changes needed?

## ✅ Action Items
- [ ] Specific task 1
- [ ] Specific task 2
- [ ] Specific task 3

Format as structured markdown with clear sections and actionable items.''',
        instructions='Generate comprehensive, actionable documentation updates based on the code changes.',
        temperature=0.2,
        top_p=0.7,
        max_tokens=1500
    )
    
    # Task 5b: Generate simple acknowledgment (if documentation not required)
    skip_documentation_task = SimpleTask(
        task_def_name='skip_documentation_task',
        task_reference_name='skip_docs_ref',
        inputs={
            'reason': 'Documentation updates not required based on change analysis',
            'pr_analysis': '${analyze_pr_webhook_ref.output}'
        }
    )
    
    # Task 6: Generate GitHub comment with AI insights
    generate_pr_comment_task = LlmGenerateTask(
        task_reference_name='generate_pr_comment_ref',
        llm_provider='google_vertex_ai',
        model='gemini-pro',
        prompt='''You are DocuSync AI, a helpful assistant that reviews pull requests and provides documentation insights. Create a friendly, professional GitHub comment for this PR.

PR Analysis Results:
${generate_ai_summary_ref.output}

Documentation Assessment:
- Requires Documentation: ${analyze_pr_webhook_ref.output.requires_documentation} 
- Priority: ${assess_priority_ref.output.priority}

Documentation Details (if applicable):
${generate_documentation_ref.output}

Create a GitHub comment with the following structure:

## 🤖 DocuSync AI Review

### 📊 Change Analysis
[Include the AI summary here in a concise format]

### 📚 Documentation Status
[If documentation is required, include key points and action items]
[If not required, acknowledge this clearly]

### 🎯 Next Steps
[Provide 2-3 actionable next steps for the PR author]

Use friendly, professional tone with appropriate emojis. Keep it concise but helpful.
If no documentation is needed, focus on acknowledging the good work and providing the change summary.''',
        instructions='Create a helpful, professional GitHub comment for the PR author.',
        temperature=0.4,
        top_p=0.8,
        max_tokens=1000
    )
    
    # Task 7: Post the GitHub comment
    post_github_comment_task = SimpleTask(
        task_def_name='post_github_comment',
        task_reference_name='post_github_comment_ref',
        inputs={
            'pr_analysis': '${analyze_pr_webhook_ref.output}',
            'ai_summary': '${generate_ai_summary_ref.output}',
            'ai_comment': '${generate_pr_comment_ref.output}',
            'documentation_result': '${documentation_required_switch.output}',
            'documentation_suggestions': '${generate_documentation_ref.output}',
            'webhook_payload': '${workflow.input.webhook_payload}'
        }
    )
    
    # Build the workflow
    workflow >> analyze_pr_task >> generate_ai_summary_task >> extract_changes_task >> assess_priority_task >> documentation_switch
    
    # Documentation branch (if required)
    documentation_switch.switch_case('true', 
        generate_documentation_task >> generate_pr_comment_task >> post_github_comment_task
    )
    
    # No documentation branch  
    documentation_switch.switch_case('false',
        skip_documentation_task >> generate_pr_comment_task >> post_github_comment_task
    )
    
    # Default case
    documentation_switch.default_case(
        skip_documentation_task >> generate_pr_comment_task >> post_github_comment_task
    )
    
    return workflow


def create_feedback_enhancement_workflow() -> ConductorWorkflow:
    """
    Workflow for processing user feedback and generating AI-powered documentation improvements.
    """
    
    workflow = ConductorWorkflow(
        name='ai_feedback_enhancement_workflow',
        version=1,
        description='AI-powered feedback processing with Gemini-generated improvements'
    )
    
    # Task 1: Analyze feedback content
    analyze_feedback_task = SimpleTask(
        task_def_name='analyze_feedback_content',
        task_reference_name='analyze_feedback_ref',
        inputs={
            'feedback_data': '${workflow.input.feedback_data}'
        }
    )
    
    # Task 2: Generate AI-powered improvement suggestions using Gemini
    generate_improvements_task = LlmGenerateTask(
        task_reference_name='generate_improvements_ref',
        llm_provider='google_vertex_ai',
        model='gemini-pro',
        prompt='''You are a documentation improvement specialist. Analyze the following user feedback and generate specific, actionable improvements.

Feedback Details:
- Source: ${workflow.input.feedback_data.source}
- Type: ${workflow.input.feedback_data.type}
- Content: ${workflow.input.feedback_data.content}
- Context: ${workflow.input.feedback_data.context}

Analysis Results:
${analyze_feedback_ref.output}

Generate improvements in this format:

## 🎯 Feedback Summary
Brief summary of the user's concern or suggestion

## 📋 Recommended Improvements

### 1. Content Changes
- Specific text/section to modify
- Proposed new content
- Rationale for change

### 2. Structure Changes  
- Organizational improvements
- New sections to add
- Sections to restructure

### 3. Examples & Code
- New examples needed
- Updated code samples
- Additional clarifications

## ⚡ Quick Wins
- 3-5 immediate improvements that can be made
- Low-effort, high-impact changes

## 🔄 Long-term Enhancements
- Bigger improvements for future consideration

## ✅ Implementation Plan
- [ ] Step 1
- [ ] Step 2  
- [ ] Step 3

Prioritize user experience and clarity. Be specific and actionable.''',
        instructions='Generate specific, actionable documentation improvements based on user feedback.',
        temperature=0.3,
        top_p=0.7,
        max_tokens=1200
    )
    
    # Task 3: Validate and score the improvements
    validate_improvements_task = SimpleTask(
        task_def_name='validate_improvement_suggestions',
        task_reference_name='validate_improvements_ref',
        inputs={
            'suggestions': '${generate_improvements_ref.output}',
            'feedback_data': '${workflow.input.feedback_data}'
        }
    )
    
    # Decision: Auto-approve or require human review
    approval_switch = SwitchTask(
        task_reference_name='approval_required_switch',
        case_expression='${validate_improvements_ref.output.confidence_score}',
        use_javascript=True,
        evaluator_type='javascript',
        expression='$.confidence_score > 0.8 ? "auto_approve" : "human_review"'
    )
    
    # Auto-approval path
    auto_approve_task = SimpleTask(
        task_def_name='auto_approve_documentation_changes',
        task_reference_name='auto_approve_ref',
        inputs={
            'suggestions': '${generate_improvements_ref.output}',
            'validation': '${validate_improvements_ref.output}'
        }
    )
    
    # Human review path
    queue_review_task = SimpleTask(
        task_def_name='queue_for_human_review',
        task_reference_name='queue_review_ref',
        inputs={
            'suggestions': '${generate_improvements_ref.output}',
            'validation': '${validate_improvements_ref.output}'
        }
    )
    
    # Notification task
    send_notification_task = SimpleTask(
        task_def_name='send_feedback_notification',
        task_reference_name='send_notification_ref',
        inputs={
            'feedback_data': '${workflow.input.feedback_data}',
            'processing_result': '${approval_required_switch.output}',
            'improvements': '${generate_improvements_ref.output}'
        }
    )
    
    # Build workflow
    workflow >> analyze_feedback_task >> generate_improvements_task >> validate_improvements_task >> approval_switch
    
    # Approval branches
    approval_switch.switch_case('auto_approve', auto_approve_task >> send_notification_task)
    approval_switch.switch_case('human_review', queue_review_task >> send_notification_task)
    approval_switch.default_case(queue_review_task >> send_notification_task)
    
    return workflow


# Workflow registration helper
def register_enhanced_workflows(workflow_client):
    """Register all enhanced workflows with Orkes."""
    
    workflows = [
        create_enhanced_pr_documentation_workflow(),
        create_feedback_enhancement_workflow()
    ]
    
    for workflow in workflows:
        try:
            workflow_client.register_workflow(workflow)
            print(f"✅ Successfully registered workflow: {workflow.name}")
        except Exception as e:
            print(f"❌ Failed to register workflow {workflow.name}: {e}")
    
    return workflows