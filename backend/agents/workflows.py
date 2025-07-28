from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.simple_task import SimpleTask
from conductor.client.workflow.task.switch_task import SwitchTask
from conductor.client.workflow.task.fork_join_task import ForkJoinTask


def create_pr_analysis_workflow() -> ConductorWorkflow:
    """
    Create the main PR analysis workflow that orchestrates the commit watcher agent
    and subsequent documentation processing steps.
    """
    
    workflow = ConductorWorkflow(
        name='pr_documentation_workflow',
        version=1,
        description='Analyzes PR changes and determines documentation requirements'
    )
    
    # Task 1: Analyze PR webhook payload
    analyze_pr_task = SimpleTask(
        task_def_name='analyze_pr_webhook',
        task_reference_name='analyze_pr_webhook_ref',
        inputs={
            'webhook_payload': '${workflow.input.webhook_payload}'
        }
    )
    
    # Task 2: Extract PR changes (parallel to analysis)
    extract_changes_task = SimpleTask(
        task_def_name='extract_pr_changes',
        task_reference_name='extract_pr_changes_ref',
        inputs={
            'pr_data': '${analyze_pr_webhook_ref.output}'
        }
    )
    
    # Task 3: Assess documentation priority
    assess_priority_task = SimpleTask(
        task_def_name='assess_documentation_priority',
        task_reference_name='assess_priority_ref',
        inputs={
            'changes_data': '${extract_pr_changes_ref.output}'
        }
    )
    
    # Task 3.5: Generate AI-powered change summary using Orkes LLM (Gemini)
    generate_summary_task = LlmGenerateTask(
        task_reference_name='generate_summary_ref',
        llm_provider='google_vertex_ai',
        model='gemini-pro',
        prompt='''You are a code analysis expert. Analyze the following PR diff and provide a clear, concise summary of the changes.

PR Information:
- Repository: ${analyze_pr_webhook_ref.output.repository}
- PR Title: ${analyze_pr_webhook_ref.output.pr_title}
- Files Changed: ${analyze_pr_webhook_ref.output.changes_summary.files_changed}

Diff:
${analyze_pr_webhook_ref.output.diff_preview}

Provide a summary in the following format:
**Summary**: Brief description of what was changed
**Impact**: What areas of the codebase/functionality are affected
**Type**: (e.g., Feature Addition, Bug Fix, Refactoring, Documentation Update)
**Technical Details**: Key technical changes made

Keep it concise but informative (max 200 words).''',
        instructions='Generate a clear, technical summary of the PR changes for developers.',
        temperature=0.2,
        top_p=0.7,
        max_tokens=500
    )
    
    # Decision task: Determine if documentation update is needed
    documentation_switch = SwitchTask(
        task_reference_name='documentation_required_switch',
        case_expression='${analyze_pr_webhook_ref.output.requires_documentation}',
        use_javascript=False
    )
    
    # Task 4a: Generate documentation updates using Orkes LLM (Gemini)
    generate_docs_task = LlmGenerateTask(
        task_reference_name='generate_docs_ref',
        llm_provider='google_vertex_ai',  # Orkes supports Gemini via Vertex AI
        model='gemini-pro',
        prompt='''You are a technical documentation expert. Analyze the following PR changes and generate comprehensive documentation updates.

PR Information:
- Repository: ${analyze_pr_webhook_ref.output.repository}
- PR Title: ${analyze_pr_webhook_ref.output.pr_title}
- Author: ${analyze_pr_webhook_ref.output.pr_author}
- Files Changed: ${analyze_pr_webhook_ref.output.changes_summary.files_changed}
- Priority: ${assess_priority_ref.output.priority}

Diff Changes:
${analyze_pr_webhook_ref.output.diff_preview}

Please provide:
1. **Change Summary**: A concise overview of what was modified
2. **Documentation Impact**: Areas of documentation that need updates
3. **Suggested Documentation Changes**: Specific recommendations for documentation updates
4. **Code Examples**: If applicable, provide updated code examples
5. **Breaking Changes**: Highlight any breaking changes that need special attention

Format your response as structured markdown.''',
        instructions='Generate clear, actionable documentation recommendations based on the PR changes.',
        temperature=0.3,
        top_p=0.8,
        max_tokens=2000
    )
    
    # Task 4b: Skip documentation (if not required)
    skip_docs_task = SimpleTask(
        task_def_name='skip_documentation_task',
        task_reference_name='skip_docs_ref',
        inputs={
            'reason': 'No documentation updates required',
            'pr_analysis': '${analyze_pr_webhook_ref.output}'
        }
    )
    
    # Task 5: Post GitHub comment with results
    post_comment_task = SimpleTask(
        task_def_name='post_github_comment',
        task_reference_name='post_comment_ref',
        inputs={
            'pr_analysis': '${analyze_pr_webhook_ref.output}',
            'ai_summary': '${generate_summary_ref.output}',
            'documentation_result': '${documentation_required_switch.output}',
            'documentation_suggestions': '${generate_docs_ref.output}',
            'webhook_payload': '${workflow.input.webhook_payload}'
        }
    )
    
    # Build workflow structure
    workflow >> analyze_pr_task >> extract_changes_task >> generate_summary_task >> assess_priority_task >> documentation_switch
    
    # Add switch cases
    documentation_switch.switch_case('true', generate_docs_task >> post_comment_task)
    documentation_switch.switch_case('false', skip_docs_task >> post_comment_task)
    documentation_switch.default_case(skip_docs_task >> post_comment_task)
    
    return workflow


def create_feedback_processing_workflow() -> ConductorWorkflow:
    """
    Create workflow for processing reader feedback and generating documentation improvements.
    """
    
    workflow = ConductorWorkflow(
        name='feedback_processing_workflow',
        version=1,
        description='Processes reader feedback and generates documentation improvements'
    )
    
    # Task 1: Analyze feedback content
    analyze_feedback_task = SimpleTask(
        task_def_name='analyze_feedback_content',
        task_reference_name='analyze_feedback_ref',
        inputs={
            'feedback_data': '${workflow.input.feedback_data}'
        }
    )
    
    # Task 2: Generate improvement suggestions
    generate_improvements_task = SimpleTask(
        task_def_name='generate_improvement_suggestions',
        task_reference_name='generate_improvements_ref',
        inputs={
            'feedback_analysis': '${analyze_feedback_ref.output}'
        }
    )
    
    # Task 3: Validate suggestions
    validate_suggestions_task = SimpleTask(
        task_def_name='validate_improvement_suggestions',
        task_reference_name='validate_suggestions_ref',
        inputs={
            'suggestions': '${generate_improvements_ref.output}'
        }
    )
    
    # Decision: Auto-approve or require human review
    approval_switch = SwitchTask(
        task_reference_name='approval_required_switch',
        case_expression='${validate_suggestions_ref.output.confidence_score}',
        use_javascript=True,
        evaluator_type='javascript',
        expression='$.confidence_score > 0.8 ? "auto_approve" : "human_review"'
    )
    
    # Task 4a: Auto-approve and apply changes
    auto_approve_task = SimpleTask(
        task_def_name='auto_approve_documentation_changes',
        task_reference_name='auto_approve_ref',
        inputs={
            'suggestions': '${generate_improvements_ref.output}',
            'validation': '${validate_suggestions_ref.output}'
        }
    )
    
    # Task 4b: Queue for human review
    queue_review_task = SimpleTask(
        task_def_name='queue_for_human_review',
        task_reference_name='queue_review_ref',
        inputs={
            'suggestions': '${generate_improvements_ref.output}',
            'validation': '${validate_suggestions_ref.output}'
        }
    )
    
    # Task 5: Send notification
    send_notification_task = SimpleTask(
        task_def_name='send_feedback_notification',
        task_reference_name='send_notification_ref',
        inputs={
            'feedback_data': '${workflow.input.feedback_data}',
            'processing_result': '${approval_required_switch.output}'
        }
    )
    
    # Build workflow structure
    workflow >> analyze_feedback_task >> generate_improvements_task >> validate_suggestions_task >> approval_switch
    
    # Add switch cases
    approval_switch.switch_case('auto_approve', auto_approve_task >> send_notification_task)
    approval_switch.switch_case('human_review', queue_review_task >> send_notification_task)
    approval_switch.default_case(queue_review_task >> send_notification_task)
    
    return workflow


def create_parallel_pr_processing_workflow() -> ConductorWorkflow:
    """
    Create a more complex workflow that processes multiple aspects of a PR in parallel.
    """
    
    workflow = ConductorWorkflow(
        name='parallel_pr_processing_workflow',
        version=1,
        description='Processes PR with parallel analysis of different aspects'
    )
    
    # Initial PR analysis
    analyze_pr_task = SimpleTask(
        task_def_name='analyze_pr_webhook',
        task_reference_name='analyze_pr_ref',
        inputs={
            'webhook_payload': '${workflow.input.webhook_payload}'
        }
    )
    
    # Parallel processing tasks
    fork_join = ForkJoinTask(
        task_reference_name='parallel_analysis_fork',
        fork_tasks=[
            [
                SimpleTask(
                    task_def_name='extract_pr_changes',
                    task_reference_name='extract_changes_fork_ref',
                    inputs={'pr_data': '${analyze_pr_ref.output}'}
                ),
                SimpleTask(
                    task_def_name='assess_documentation_priority',
                    task_reference_name='assess_priority_fork_ref',
                    inputs={'changes_data': '${extract_changes_fork_ref.output}'}
                )
            ],
            [
                SimpleTask(
                    task_def_name='analyze_code_quality',
                    task_reference_name='analyze_quality_ref',
                    inputs={'pr_data': '${analyze_pr_ref.output}'}
                )
            ],
            [
                SimpleTask(
                    task_def_name='check_existing_documentation',
                    task_reference_name='check_docs_ref',
                    inputs={'pr_data': '${analyze_pr_ref.output}'}
                )
            ]
        ]
    )
    
    # Consolidate results
    consolidate_task = SimpleTask(
        task_def_name='consolidate_analysis_results',
        task_reference_name='consolidate_ref',
        inputs={
            'pr_analysis': '${analyze_pr_ref.output}',
            'priority_assessment': '${assess_priority_fork_ref.output}',
            'quality_analysis': '${analyze_quality_ref.output}',
            'existing_docs': '${check_docs_ref.output}'
        }
    )
    
    # Final decision and action
    final_action_task = SimpleTask(
        task_def_name='execute_final_actions',
        task_reference_name='final_action_ref',
        inputs={
            'consolidated_analysis': '${consolidate_ref.output}',
            'webhook_payload': '${workflow.input.webhook_payload}'
        }
    )
    
    # Build workflow
    workflow >> analyze_pr_task >> fork_join >> consolidate_task >> final_action_task
    
    return workflow


# Workflow registration helper
def register_workflows(workflow_client):
    """Register all workflows with the Conductor server."""
    
    workflows = [
        create_pr_analysis_workflow(),
        create_feedback_processing_workflow(),
        create_parallel_pr_processing_workflow()
    ]
    
    for workflow in workflows:
        try:
            workflow_client.register_workflow(workflow)
            print(f"Successfully registered workflow: {workflow.name}")
        except Exception as e:
            print(f"Failed to register workflow {workflow.name}: {e}")
    
    return workflows