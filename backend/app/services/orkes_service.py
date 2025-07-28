from conductor.client.configuration.configuration import Configuration
from conductor.client.orkes_clients import OrkesClients
from conductor.client.worker.worker_interface import WorkerInterface
from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.task_type import TaskType
from typing import Optional, Dict, Any, List
import asyncio
import json
from datetime import datetime

from app.core.config import settings


class OrkesService:
    """Service for interacting with Orkes workflow orchestration"""
    
    def __init__(self):
        try:
            self.config = Configuration(
                server_api_url=settings.orkes_server_url,
                debug=settings.debug
            )
            
            # Set authentication token directly if available
            if settings.orkes_api_key:
                self.config.access_token = settings.orkes_api_key
            
            self.clients = OrkesClients(configuration=self.config)
            self.workflow_client = self.clients.get_workflow_client()
            self.task_client = self.clients.get_task_client()
            
        except Exception as e:
            print(f"Warning: Orkes client initialization failed: {e}")
            # Set clients to None so we can handle gracefully
            self.clients = None
            self.workflow_client = None
            self.task_client = None
    
    def _is_available(self) -> bool:
        """Check if Orkes client is available"""
        return self.workflow_client is not None
    
    async def start_workflow(self, workflow_name: str, input_data: Dict[str, Any], correlation_id: Optional[str] = None) -> Optional[str]:
        """Start a new workflow execution"""
        if not self._is_available():
            print("Warning: Orkes client not initialized, skipping workflow start")
            return None
            
        try:
            workflow_id = self.workflow_client.start_workflow(
                name=workflow_name,
                input=input_data,
                version=1,
                correlation_id=correlation_id
            )
            
            print(f"Started workflow {workflow_name} with ID: {workflow_id}")
            return workflow_id
            
        except Exception as e:
            print(f"Error starting workflow: {e}")
            return None
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status"""
        if not self._is_available():
            print("Warning: Orkes client not initialized, skipping workflow status check")
            return None
            
        try:
            workflow = self.workflow_client.get_workflow(workflow_id, include_tasks=True)
            
            return {
                "workflow_id": workflow.workflow_id,
                "status": workflow.status.name,
                "start_time": workflow.start_time,
                "end_time": workflow.end_time,
                "correlation_id": workflow.correlation_id,
                "input": workflow.input,
                "output": workflow.output,
                "reason_for_incompletion": workflow.reason_for_incompletion,
                "tasks": [
                    {
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "status": task.status.name,
                        "start_time": task.start_time,
                        "end_time": task.end_time,
                        "execution_time": task.end_time - task.start_time if task.end_time and task.start_time else None,
                        "output_data": task.output_data,
                        "reason_for_incompletion": task.reason_for_incompletion
                    } for task in (workflow.tasks or [])
                ]
            }
            
        except Exception as e:
            print(f"Error getting workflow status: {e}")
            return None
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        if not self._is_available():
            print("Warning: Orkes client not initialized, skipping workflow cancellation")
            return False
            
        try:
            self.workflow_client.terminate_workflow(workflow_id, reason="User requested cancellation")
            print(f"Cancelled workflow: {workflow_id}")
            return True
            
        except Exception as e:
            print(f"Error cancelling workflow: {e}")
            return False
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow"""
        if not self._is_available():
            print("Warning: Orkes client not initialized, skipping workflow pause")
            return False
            
        try:
            self.workflow_client.pause_workflow(workflow_id)
            print(f"Paused workflow: {workflow_id}")
            return True
            
        except Exception as e:
            print(f"Error pausing workflow: {e}")
            return False
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        if not self._is_available():
            print("Warning: Orkes client not initialized, skipping workflow resume")
            return False
            
        try:
            self.workflow_client.resume_workflow(workflow_id)
            print(f"Resumed workflow: {workflow_id}")
            return True
            
        except Exception as e:
            print(f"Error resuming workflow: {e}")
            return False
    
    async def retry_workflow(self, original_workflow_id: str, trigger_event: Dict[str, Any], repo_info: Dict[str, Any]) -> Optional[str]:
        """Retry a failed workflow with same inputs"""
        try:
            # Get original workflow details
            original_workflow = self.workflow_client.get_workflow(original_workflow_id)
            
            if not original_workflow:
                return None
            
            # Start new workflow with same input
            new_workflow_id = await self.start_workflow(
                workflow_name="docusync_main_workflow",
                input_data=original_workflow.input,
                correlation_id=f"retry_{original_workflow_id}"
            )
            
            return new_workflow_id
            
        except Exception as e:
            print(f"Error retrying workflow: {e}")
            return None
    
    async def trigger_initial_scan(self, repo_id: str, repo_info: Dict[str, Any]) -> Optional[str]:
        """Trigger initial documentation scan for new repository"""
        try:
            workflow_input = {
                "event_type": "initial_scan",
                "repo_id": repo_id,
                "repository": repo_info,
                "scan_config": {
                    "full_scan": True,
                    "generate_missing_docs": True,
                    "validate_existing_docs": True
                }
            }
            
            workflow_id = await self.start_workflow(
                "docusync_initial_scan_workflow",
                workflow_input,
                correlation_id=f"initial_scan_{repo_id}"
            )
            
            return workflow_id
            
        except Exception as e:
            print(f"Error triggering initial scan: {e}")
            return None
    
    async def trigger_manual_sync(self, repo_id: str, repo_info: Dict[str, Any]) -> Optional[str]:
        """Trigger manual documentation sync"""
        try:
            workflow_input = {
                "event_type": "manual_sync",
                "repo_id": repo_id,
                "repository": repo_info,
                "sync_config": {
                    "force_update": True,
                    "validate_all": True
                }
            }
            
            workflow_id = await self.start_workflow(
                "docusync_main_workflow",
                workflow_input,
                correlation_id=f"manual_sync_{repo_id}_{int(datetime.now().timestamp())}"
            )
            
            return workflow_id
            
        except Exception as e:
            print(f"Error triggering manual sync: {e}")
            return None
    
    async def trigger_feedback_workflow(self, feedback_id: str, repo_info: Dict[str, Any], feedback_data: Dict[str, Any]) -> Optional[str]:
        """Trigger feedback processing workflow"""
        try:
            workflow_input = {
                "event_type": "feedback_processing",
                "feedback_id": feedback_id,
                "repository": repo_info,
                "feedback_data": feedback_data,
                "processing_config": {
                    "generate_suggestion": True,
                    "validate_suggestion": True,
                    "auto_approve_threshold": 0.9
                }
            }
            
            workflow_id = await self.start_workflow(
                "docusync_feedback_workflow",
                workflow_input,
                correlation_id=f"feedback_{feedback_id}"
            )
            
            return workflow_id
            
        except Exception as e:
            print(f"Error triggering feedback workflow: {e}")
            return None
    
    async def trigger_feedback_regeneration(self, feedback_id: str, repo_info: Dict[str, Any], feedback_data: Dict[str, Any]) -> Optional[str]:
        """Trigger feedback suggestion regeneration"""
        try:
            workflow_input = {
                "event_type": "feedback_regeneration",
                "feedback_id": feedback_id,
                "repository": repo_info,
                "feedback_data": feedback_data,
                "regeneration_config": {
                    "force_regenerate": True,
                    "use_alternative_approach": True
                }
            }
            
            workflow_id = await self.start_workflow(
                "docusync_feedback_workflow",
                workflow_input,
                correlation_id=f"feedback_regen_{feedback_id}_{int(datetime.now().timestamp())}"
            )
            
            return workflow_id
            
        except Exception as e:
            print(f"Error triggering feedback regeneration: {e}")
            return None
    
    async def get_workflow_execution_logs(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get detailed execution logs for a workflow"""
        try:
            workflow = self.workflow_client.get_workflow(workflow_id, include_tasks=True)
            
            if not workflow:
                return []
            
            logs = []
            
            # Add workflow-level log
            logs.append({
                "timestamp": workflow.start_time,
                "level": "INFO",
                "component": "workflow",
                "message": f"Workflow {workflow.workflow_definition.name} started",
                "details": {
                    "workflow_id": workflow.workflow_id,
                    "correlation_id": workflow.correlation_id,
                    "input": workflow.input
                }
            })
            
            # Add task-level logs
            for task in (workflow.tasks or []):
                logs.append({
                    "timestamp": task.start_time,
                    "level": "INFO",
                    "component": f"task_{task.task_type}",
                    "message": f"Task {task.task_type} started",
                    "details": {
                        "task_id": task.task_id,
                        "input_data": task.input_data
                    }
                })
                
                if task.end_time:
                    logs.append({
                        "timestamp": task.end_time,
                        "level": "INFO" if task.status.name == "COMPLETED" else "ERROR",
                        "component": f"task_{task.task_type}",
                        "message": f"Task {task.task_type} {task.status.name.lower()}",
                        "details": {
                            "task_id": task.task_id,
                            "status": task.status.name,
                            "output_data": task.output_data,
                            "execution_time_ms": (task.end_time - task.start_time) if task.start_time else None,
                            "reason_for_incompletion": task.reason_for_incompletion
                        }
                    })
            
            # Add workflow completion log
            if workflow.end_time:
                logs.append({
                    "timestamp": workflow.end_time,
                    "level": "INFO" if workflow.status.name == "COMPLETED" else "ERROR",
                    "component": "workflow",
                    "message": f"Workflow {workflow.status.name.lower()}",
                    "details": {
                        "workflow_id": workflow.workflow_id,
                        "status": workflow.status.name,
                        "output": workflow.output,
                        "total_execution_time_ms": (workflow.end_time - workflow.start_time) if workflow.start_time else None,
                        "reason_for_incompletion": workflow.reason_for_incompletion
                    }
                })
            
            # Sort logs by timestamp
            logs.sort(key=lambda x: x["timestamp"] or 0)
            
            return logs
            
        except Exception as e:
            print(f"Error getting workflow execution logs: {e}")
            return []
    
    async def get_workflow_metrics(self, workflow_name: str, start_time: Optional[int] = None, end_time: Optional[int] = None) -> Dict[str, Any]:
        """Get workflow execution metrics"""
        try:
            # This would use Orkes metrics API when available
            # For now, return mock data structure
            
            metrics = {
                "workflow_name": workflow_name,
                "time_range": {
                    "start": start_time,
                    "end": end_time
                },
                "execution_stats": {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "success_rate": 0.0,
                    "average_execution_time_ms": 0,
                    "median_execution_time_ms": 0,
                    "p95_execution_time_ms": 0
                },
                "task_stats": [],
                "failure_reasons": []
            }
            
            return metrics
            
        except Exception as e:
            print(f"Error getting workflow metrics: {e}")
            return {}
    
    async def register_workflow_definition(self, workflow_definition: Dict[str, Any]) -> bool:
        """Register a new workflow definition"""
        try:
            # This would register workflow definition with Orkes
            # Implementation depends on Orkes Python SDK
            
            print(f"Registering workflow definition: {workflow_definition.get('name')}")
            return True
            
        except Exception as e:
            print(f"Error registering workflow definition: {e}")
            return False
    
    async def update_workflow_definition(self, workflow_definition: Dict[str, Any]) -> bool:
        """Update existing workflow definition"""
        try:
            # This would update workflow definition in Orkes
            
            print(f"Updating workflow definition: {workflow_definition.get('name')}")
            return True
            
        except Exception as e:
            print(f"Error updating workflow definition: {e}")
            return False