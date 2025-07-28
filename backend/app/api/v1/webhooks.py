from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib
import json

from app.core.config import settings
from app.services.supabase_service import SupabaseService
from app.services.orkes_service import OrkesService
from app.middleware.error_handler import GitHubAPIError

router = APIRouter()

supabase_service = SupabaseService()
orkes_service = OrkesService()


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature:
        return False
    
    try:
        # Remove 'sha256=' prefix
        signature = signature.replace('sha256=', '')
        
        # Calculate expected signature
        expected_signature = hmac.new(
            settings.github_webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Secure comparison
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        print(f"Signature verification error: {e}")
        return False


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None)
):
    """Handle GitHub webhook events"""
    try:
        # Read payload
        payload = await request.body()
        
        # Verify signature
        if not verify_github_signature(payload, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        try:
            event_data = json.loads(payload.decode())
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Extract repository information
        repository = event_data.get('repository', {})
        repo_full_name = repository.get('full_name')
        
        if not repo_full_name:
            return {"message": "No repository information found"}
        
        # Check if repository is monitored
        repo_result = supabase_service.supabase.table('repositories').select(
            'id', 'user_id', 'doc_config', 'status'
        ).eq('full_name', repo_full_name).eq('status', 'active').execute()
        
        if not repo_result.data:
            return {"message": f"Repository {repo_full_name} is not monitored"}
        
        monitored_repo = repo_result.data[0]
        
        # Handle different event types
        workflow_id = None
        
        if x_github_event == "push":
            workflow_id = await handle_push_event(event_data, monitored_repo)
        elif x_github_event == "pull_request":
            workflow_id = await handle_pull_request_event(event_data, monitored_repo)
        elif x_github_event == "issues":
            workflow_id = await handle_issues_event(event_data, monitored_repo)
        elif x_github_event == "ping":
            return {"message": "Webhook ping received successfully"}
        else:
            return {"message": f"Event type {x_github_event} not handled"}
        
        # Log webhook event
        await log_webhook_event(
            event_type=x_github_event,
            repo_id=monitored_repo['id'],
            delivery_id=x_github_delivery,
            workflow_id=workflow_id,
            payload_summary=extract_payload_summary(event_data, x_github_event)
        )
        
        response_data = {
            "message": f"Event {x_github_event} processed successfully",
            "repository": repo_full_name,
            "workflow_triggered": bool(workflow_id)
        }
        
        if workflow_id:
            response_data["workflow_id"] = workflow_id
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise GitHubAPIError(f"Webhook processing failed: {str(e)}")


async def handle_push_event(event_data: dict, monitored_repo: dict) -> Optional[str]:
    """Handle push events"""
    try:
        # Extract push information
        commits = event_data.get('commits', [])
        ref = event_data.get('ref', '')
        
        # Only process pushes to main/master branch by default
        if not ref.endswith(('/main', '/master')):
            return None
        
        if not commits:
            return None
        
        # Prepare workflow input
        workflow_input = {
            "event_type": "push",
            "repo_id": monitored_repo['id'],
            "repository": {
                "name": event_data['repository']['name'],
                "owner": event_data['repository']['owner']['login'],
                "full_name": event_data['repository']['full_name']
            },
            "payload": {
                "ref": ref,
                "commits": commits,
                "head_commit": event_data.get('head_commit'),
                "pusher": event_data.get('pusher')
            },
            "doc_config": monitored_repo['doc_config']
        }
        
        # Trigger main workflow
        workflow_id = await orkes_service.start_workflow(
            "docusync_main_workflow",
            workflow_input
        )
        
        return workflow_id
        
    except Exception as e:
        print(f"Error handling push event: {e}")
        return None


async def handle_pull_request_event(event_data: dict, monitored_repo: dict) -> Optional[str]:
    """Handle pull request events"""
    try:
        action = event_data.get('action')
        
        # Only process certain PR actions
        if action not in ['opened', 'synchronize', 'reopened']:
            return None
        
        pull_request = event_data.get('pull_request', {})
        
        # Prepare workflow input
        workflow_input = {
            "event_type": "pull_request",
            "repo_id": monitored_repo['id'],
            "repository": {
                "name": event_data['repository']['name'],
                "owner": event_data['repository']['owner']['login'],
                "full_name": event_data['repository']['full_name']
            },
            "payload": {
                "action": action,
                "number": pull_request.get('number'),
                "title": pull_request.get('title'),
                "body": pull_request.get('body'),
                "head": pull_request.get('head', {}),
                "base": pull_request.get('base', {}),
                "user": pull_request.get('user', {}),
                "html_url": pull_request.get('html_url')
            },
            "doc_config": monitored_repo['doc_config']
        }
        
        # Trigger main workflow
        workflow_id = await orkes_service.start_workflow(
            "docusync_main_workflow",
            workflow_input
        )
        
        return workflow_id
        
    except Exception as e:
        print(f"Error handling pull request event: {e}")
        return None


async def handle_issues_event(event_data: dict, monitored_repo: dict) -> Optional[str]:
    """Handle issues events (for documentation feedback)"""
    try:
        action = event_data.get('action')
        
        # Only process issue creation
        if action != 'opened':
            return None
        
        issue = event_data.get('issue', {})
        
        # Check if issue is related to documentation
        title = issue.get('title', '').lower()
        body = issue.get('body', '').lower()
        labels = [label.get('name', '').lower() for label in issue.get('labels', [])]
        
        doc_keywords = ['documentation', 'docs', 'readme', 'guide', 'tutorial', 'example']
        
        is_doc_related = (
            any(keyword in title for keyword in doc_keywords) or
            any(keyword in body for keyword in doc_keywords) or
            any(keyword in label for label in labels for keyword in doc_keywords)
        )
        
        if not is_doc_related:
            return None
        
        # Create feedback record
        feedback_data = {
            'repo_id': monitored_repo['id'],
            'file_path': 'general',  # Issue doesn't specify a file
            'section': None,
            'feedback_type': 'user_confusion',
            'feedback_text': f"GitHub Issue: {issue.get('title', '')}\n\n{issue.get('body', '')}",
            'status': 'pending',
            'triggered_by': {
                'type': 'github_issue',
                'event_id': str(issue.get('id')),
                'user': issue.get('user', {}).get('login'),
                'issue_url': issue.get('html_url')
            }
        }
        
        feedback_result = supabase_service.supabase.table('doc_feedback').insert(
            feedback_data
        ).execute()
        
        if feedback_result.data:
            # Trigger feedback processing workflow
            workflow_id = await orkes_service.trigger_feedback_workflow(
                feedback_id=feedback_result.data[0]['id'],
                repo_info={
                    'id': monitored_repo['id'],
                    'name': event_data['repository']['name'],
                    'owner': event_data['repository']['owner']['login']
                },
                feedback_data=feedback_data
            )
            
            return workflow_id
        
        return None
        
    except Exception as e:
        print(f"Error handling issues event: {e}")
        return None


async def log_webhook_event(
    event_type: str,
    repo_id: str,
    delivery_id: Optional[str],
    workflow_id: Optional[str],
    payload_summary: dict
):
    """Log webhook event for debugging and monitoring"""
    try:
        log_data = {
            'event_type': event_type,
            'repo_id': repo_id,
            'delivery_id': delivery_id,
            'workflow_id': workflow_id,
            'payload_summary': payload_summary,
            'processed_at': 'now()'
        }
        
        # In a real implementation, you might want a separate webhook_logs table
        # For now, we'll just print for debugging
        print(f"Webhook event logged: {log_data}")
        
    except Exception as e:
        print(f"Error logging webhook event: {e}")


def extract_payload_summary(event_data: dict, event_type: str) -> dict:
    """Extract relevant summary information from webhook payload"""
    summary = {
        "event_type": event_type,
        "repository": event_data.get('repository', {}).get('full_name'),
        "sender": event_data.get('sender', {}).get('login')
    }
    
    if event_type == "push":
        summary.update({
            "ref": event_data.get('ref'),
            "commits_count": len(event_data.get('commits', [])),
            "head_commit": event_data.get('head_commit', {}).get('id', '')[:7]
        })
    elif event_type == "pull_request":
        pr = event_data.get('pull_request', {})
        summary.update({
            "action": event_data.get('action'),
            "pr_number": pr.get('number'),
            "pr_title": pr.get('title', '')[:100]  # Truncate long titles
        })
    elif event_type == "issues":
        issue = event_data.get('issue', {})
        summary.update({
            "action": event_data.get('action'),
            "issue_number": issue.get('number'),
            "issue_title": issue.get('title', '')[:100]
        })
    
    return summary


@router.get("/github/status")
async def github_webhook_status():
    """Get GitHub webhook status and health"""
    try:
        # Check webhook configuration
        webhook_configured = bool(settings.github_webhook_secret)
        
        # Get recent webhook events count (would query webhook_logs table in real implementation)
        recent_events_count = 0  # Placeholder
        
        return {
            "success": True,
            "data": {
                "webhook_configured": webhook_configured,
                "webhook_url": "/webhooks/github",
                "recent_events_24h": recent_events_count,
                "supported_events": [
                    "push",
                    "pull_request",
                    "issues"
                ],
                "status": "operational"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get webhook status: {str(e)}")