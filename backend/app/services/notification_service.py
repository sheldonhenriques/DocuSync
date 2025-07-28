from typing import Optional, Dict, Any, List
import httpx
import json
from datetime import datetime

from app.core.config import settings


class NotificationService:
    """Service for sending notifications via various channels"""
    
    def __init__(self):
        self.slack_timeout = 10
        self.email_timeout = 30
    
    async def send_slack_notification(self, webhook_url: str, message: Dict[str, Any]) -> bool:
        """Send notification to Slack webhook"""
        try:
            if not webhook_url:
                return False
            
            async with httpx.AsyncClient(timeout=self.slack_timeout) as client:
                response = await client.post(
                    webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print(f"Slack notification sent successfully")
                    return True
                else:
                    print(f"Slack notification failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False
    
    async def send_workflow_completion_notification(self, workflow_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> bool:
        """Send notification when workflow completes"""
        try:
            # Check if notifications are enabled
            if not user_preferences.get('notifications_enabled', True):
                return True
            
            status = workflow_data.get('status', 'unknown')
            repo_name = workflow_data.get('repository', {}).get('name', 'Unknown')
            
            # Prepare notification content
            if status == 'completed':
                color = "good"
                title = "✅ Documentation Updated Successfully"
                message = f"Documentation has been automatically updated for *{repo_name}*"
            elif status == 'failed':
                color = "danger"
                title = "❌ Documentation Update Failed"
                message = f"Documentation update failed for *{repo_name}*"
            else:
                color = "warning"
                title = f"🔄 Documentation Update {status.title()}"
                message = f"Documentation update for *{repo_name}* is {status}"
            
            # Get results summary
            results = workflow_data.get('results', {})
            docs_updated = results.get('docs_updated', 0)
            validation_passed = results.get('validation_passed', True)
            
            fields = [
                {
                    "title": "Repository",
                    "value": repo_name,
                    "short": True
                },
                {
                    "title": "Status",
                    "value": status.title(),
                    "short": True
                }
            ]
            
            if docs_updated > 0:
                fields.append({
                    "title": "Documents Updated",
                    "value": str(docs_updated),
                    "short": True
                })
            
            if not validation_passed:
                fields.append({
                    "title": "Validation",
                    "value": "⚠️ Some validations failed",
                    "short": True
                })
            
            # Send Slack notification if configured
            slack_webhook = user_preferences.get('slack_webhook')
            if slack_webhook and user_preferences.get('slack_notifications', False):
                slack_message = {
                    "attachments": [
                        {
                            "color": color,
                            "title": title,
                            "text": message,
                            "fields": fields,
                            "footer": "DocuSync",
                            "ts": int(datetime.now().timestamp())
                        }
                    ]
                }
                
                await self.send_slack_notification(slack_webhook, slack_message)
            
            # Send email notification if configured
            if user_preferences.get('email_notifications', True):
                await self.send_email_notification(
                    recipient=user_preferences.get('email'),
                    subject=title,
                    content=message,
                    workflow_data=workflow_data
                )
            
            return True
            
        except Exception as e:
            print(f"Error sending workflow completion notification: {e}")
            return False
    
    async def send_feedback_notification(self, feedback_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> bool:
        """Send notification when new feedback is received"""
        try:
            if not user_preferences.get('notifications_enabled', True):
                return True
            
            repo_name = feedback_data.get('repo_name', 'Unknown')
            file_path = feedback_data.get('file_path', 'Unknown file')
            feedback_text = feedback_data.get('feedback_text', '')
            
            # Truncate long feedback text
            if len(feedback_text) > 200:
                feedback_text = feedback_text[:200] + "..."
            
            title = "📝 New Documentation Feedback"
            message = f"New feedback received for *{repo_name}*"
            
            fields = [
                {
                    "title": "Repository",
                    "value": repo_name,
                    "short": True
                },
                {
                    "title": "File",
                    "value": file_path,
                    "short": True
                },
                {
                    "title": "Feedback",
                    "value": feedback_text,
                    "short": False
                }
            ]
            
            # Send Slack notification
            slack_webhook = user_preferences.get('slack_webhook')
            if slack_webhook and user_preferences.get('slack_notifications', False):
                slack_message = {
                    "attachments": [
                        {
                            "color": "warning",
                            "title": title,
                            "text": message,
                            "fields": fields,
                            "footer": "DocuSync",
                            "ts": int(datetime.now().timestamp())
                        }
                    ]
                }
                
                await self.send_slack_notification(slack_webhook, slack_message)
            
            # Send email notification
            if user_preferences.get('email_notifications', True):
                await self.send_email_notification(
                    recipient=user_preferences.get('email'),
                    subject=title,
                    content=f"{message}\n\nFile: {file_path}\nFeedback: {feedback_text}",
                    feedback_data=feedback_data
                )
            
            return True
            
        except Exception as e:
            print(f"Error sending feedback notification: {e}")
            return False
    
    async def send_email_notification(self, recipient: str, subject: str, content: str, **kwargs) -> bool:
        """Send email notification (placeholder implementation)"""
        try:
            # In a real implementation, you would integrate with an email service
            # like SendGrid, AWS SES, or similar
            
            print(f"Email notification sent to {recipient}")
            print(f"Subject: {subject}")
            print(f"Content: {content}")
            
            # For now, just log the email
            return True
            
        except Exception as e:
            print(f"Error sending email notification: {e}")
            return False
    
    async def send_error_alert(self, error_data: Dict[str, Any], admin_settings: Dict[str, Any]) -> bool:
        """Send error alert to administrators"""
        try:
            error_type = error_data.get('error_type', 'Unknown Error')
            error_message = error_data.get('message', 'No details available')
            component = error_data.get('component', 'system')
            
            title = f"🚨 DocuSync Error Alert: {error_type}"
            message = f"An error occurred in the DocuSync system"
            
            fields = [
                {
                    "title": "Component",
                    "value": component,
                    "short": True
                },
                {
                    "title": "Error Type",
                    "value": error_type,
                    "short": True
                },
                {
                    "title": "Message",
                    "value": error_message,
                    "short": False
                },
                {
                    "title": "Timestamp",
                    "value": datetime.now().isoformat(),
                    "short": True
                }
            ]
            
            # Send to admin Slack channel
            admin_slack_webhook = admin_settings.get('admin_slack_webhook')
            if admin_slack_webhook:
                slack_message = {
                    "attachments": [
                        {
                            "color": "danger",
                            "title": title,
                            "text": message,
                            "fields": fields,
                            "footer": "DocuSync Error Monitor",
                            "ts": int(datetime.now().timestamp())
                        }
                    ]
                }
                
                await self.send_slack_notification(admin_slack_webhook, slack_message)
            
            return True
            
        except Exception as e:
            print(f"Error sending error alert: {e}")
            return False
    
    async def send_usage_alert(self, usage_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> bool:
        """Send usage limit alert to user"""
        try:
            if not user_preferences.get('notifications_enabled', True):
                return True
            
            limit_type = usage_data.get('limit_type', 'unknown')
            current_usage = usage_data.get('current_usage', 0)
            limit = usage_data.get('limit', 0)
            percentage = usage_data.get('percentage', 0)
            
            if percentage >= 100:
                title = f"🚨 {limit_type.title()} Limit Exceeded"
                color = "danger"
                message = f"You have exceeded your {limit_type} limit"
            elif percentage >= 90:
                title = f"⚠️ {limit_type.title()} Limit Almost Reached"
                color = "warning"
                message = f"You are approaching your {limit_type} limit"
            else:
                return True  # No alert needed
            
            fields = [
                {
                    "title": "Current Usage",
                    "value": str(current_usage),
                    "short": True
                },
                {
                    "title": "Limit",
                    "value": str(limit),
                    "short": True
                },
                {
                    "title": "Usage Percentage",
                    "value": f"{percentage:.1f}%",
                    "short": True
                }
            ]
            
            # Send Slack notification
            slack_webhook = user_preferences.get('slack_webhook')
            if slack_webhook and user_preferences.get('slack_notifications', False):
                slack_message = {
                    "attachments": [
                        {
                            "color": color,
                            "title": title,
                            "text": message,
                            "fields": fields,
                            "footer": "DocuSync Usage Monitor",
                            "ts": int(datetime.now().timestamp())
                        }
                    ]
                }
                
                await self.send_slack_notification(slack_webhook, slack_message)
            
            # Send email notification
            if user_preferences.get('email_notifications', True):
                await self.send_email_notification(
                    recipient=user_preferences.get('email'),
                    subject=title,
                    content=f"{message}\n\nCurrent usage: {current_usage}/{limit} ({percentage:.1f}%)",
                    usage_data=usage_data
                )
            
            return True
            
        except Exception as e:
            print(f"Error sending usage alert: {e}")
            return False
    
    async def send_custom_notification(self, notification_config: Dict[str, Any]) -> bool:
        """Send custom notification with specified configuration"""
        try:
            notification_type = notification_config.get('type', 'slack')
            
            if notification_type == 'slack':
                return await self.send_slack_notification(
                    webhook_url=notification_config.get('webhook_url'),
                    message=notification_config.get('message', {})
                )
            elif notification_type == 'email':
                return await self.send_email_notification(
                    recipient=notification_config.get('recipient'),
                    subject=notification_config.get('subject', 'DocuSync Notification'),
                    content=notification_config.get('content', '')
                )
            else:
                print(f"Unsupported notification type: {notification_type}")
                return False
                
        except Exception as e:
            print(f"Error sending custom notification: {e}")
            return False