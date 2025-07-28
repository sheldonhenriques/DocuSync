"""
Simplified workflows that work with the current Conductor Python SDK version.
These workflows use basic task definitions that are compatible with the installed SDK.
"""

from conductor.client.http.models.workflow_def import WorkflowDef
from conductor.client.http.models.workflow_task import WorkflowTask


def create_simple_pr_workflow() -> WorkflowDef:
    """
    Create a simple PR analysis workflow using basic WorkflowTask definitions.
    This is compatible with the current Conductor Python SDK version.
    """
    
    # Task 1: Analyze PR webhook
    analyze_task = WorkflowTask()
    analyze_task.name = "analyze_pr_webhook"
    analyze_task.task_reference_name = "analyze_pr_ref"
    analyze_task.type = "SIMPLE"
    analyze_task.input_parameters = {
        "webhook_payload": "${workflow.input.webhook_payload}"
    }
    
    # Task 2: Extract changes
    extract_task = WorkflowTask()
    extract_task.name = "extract_pr_changes" 
    extract_task.task_reference_name = "extract_changes_ref"
    extract_task.type = "SIMPLE"
    extract_task.input_parameters = {
        "pr_data": "${analyze_pr_ref.output}"
    }
    
    # Task 3: Assess priority
    priority_task = WorkflowTask()
    priority_task.name = "assess_documentation_priority"
    priority_task.task_reference_name = "assess_priority_ref"
    priority_task.type = "SIMPLE"
    priority_task.input_parameters = {
        "changes_data": "${extract_changes_ref.output}"
    }
    
    # Task 4: Post GitHub comment
    comment_task = WorkflowTask()
    comment_task.name = "post_github_comment"
    comment_task.task_reference_name = "post_comment_ref"
    comment_task.type = "SIMPLE"
    comment_task.input_parameters = {
        "pr_analysis": "${analyze_pr_ref.output}",
        "webhook_payload": "${workflow.input.webhook_payload}"
    }
    
    # Create workflow definition
    workflow_def = WorkflowDef()
    workflow_def.name = "simple_pr_workflow"
    workflow_def.version = 1
    workflow_def.description = "Simple PR analysis workflow"
    workflow_def.tasks = [analyze_task, extract_task, priority_task, comment_task]
    workflow_def.schema_version = 2
    
    return workflow_def


def register_simple_workflows(workflow_client):
    """Register simplified workflows with Conductor."""
    
    workflows = [
        create_simple_pr_workflow()
    ]
    
    for workflow in workflows:
        try:
            # Register using the workflow client
            workflow_client.register_workflow(workflow, True)  # True for overwrite
            print(f"✅ Successfully registered workflow: {workflow.name}")
        except Exception as e:
            print(f"❌ Failed to register workflow {workflow.name}: {e}")
    
    return workflows


# Alternative: Create workflow using dictionary definition
def create_workflow_dict() -> dict:
    """Create workflow as dictionary for easier registration."""
    
    return {
        "name": "docusync_pr_workflow",
        "version": 1,
        "description": "DocuSync PR analysis workflow",
        "schemaVersion": 2,
        "tasks": [
            {
                "name": "analyze_pr_webhook",
                "taskReferenceName": "analyze_pr_ref",
                "type": "SIMPLE",
                "inputParameters": {
                    "webhook_payload": "${workflow.input.webhook_payload}"
                }
            },
            {
                "name": "extract_pr_changes",
                "taskReferenceName": "extract_changes_ref", 
                "type": "SIMPLE",
                "inputParameters": {
                    "pr_data": "${analyze_pr_ref.output}"
                }
            },
            {
                "name": "assess_documentation_priority",
                "taskReferenceName": "assess_priority_ref",
                "type": "SIMPLE", 
                "inputParameters": {
                    "changes_data": "${extract_changes_ref.output}"
                }
            },
            {
                "name": "post_github_comment",
                "taskReferenceName": "post_comment_ref",
                "type": "SIMPLE",
                "inputParameters": {
                    "pr_analysis": "${analyze_pr_ref.output}",
                    "webhook_payload": "${workflow.input.webhook_payload}"
                }
            }
        ]
    }


def register_dict_workflow(workflow_client):
    """Register workflow using dictionary definition."""
    
    workflow_dict = create_workflow_dict()
    
    try:
        # Register using dictionary
        workflow_client.register_workflow_def(workflow_dict)
        print(f"✅ Successfully registered workflow: {workflow_dict['name']}")
        return True
    except Exception as e:
        print(f"❌ Failed to register workflow {workflow_dict['name']}: {e}")
        return False