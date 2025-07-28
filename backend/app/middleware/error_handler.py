from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback
import uuid
import logging
from typing import Union

from app.models.base import ErrorResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocuSyncException(Exception):
    """Base exception for DocuSync application"""
    def __init__(self, message: str, code: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class RepositoryNotFoundError(DocuSyncException):
    def __init__(self, repo_id: str):
        super().__init__(
            message=f"Repository with ID '{repo_id}' not found",
            code="REPOSITORY_NOT_FOUND",
            status_code=404,
            details={"repo_id": repo_id}
        )


class FeedbackNotFoundError(DocuSyncException):
    def __init__(self, feedback_id: str):
        super().__init__(
            message=f"Feedback with ID '{feedback_id}' not found",
            code="FEEDBACK_NOT_FOUND",
            status_code=404,
            details={"feedback_id": feedback_id}
        )


class WorkflowError(DocuSyncException):
    def __init__(self, message: str, workflow_id: str = None):
        super().__init__(
            message=f"Workflow execution failed: {message}",
            code="WORKFLOW_ERROR",
            status_code=500,
            details={"workflow_id": workflow_id} if workflow_id else {}
        )


class GitHubAPIError(DocuSyncException):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(
            message=f"GitHub API error: {message}",
            code="GITHUB_API_ERROR",
            status_code=status_code
        )


class ValidationError(DocuSyncException):
    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=f"Validation error: {message}",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field} if field else {}
        )


async def error_handler_middleware(request: Request, call_next):
    """Global error handling middleware"""
    request_id = str(uuid.uuid4())
    
    try:
        # Add request ID to request state for logging
        request.state.request_id = request_id
        response = await call_next(request)
        return response
        
    except DocuSyncException as e:
        logger.error(
            f"DocuSync error - Request ID: {request_id}, Code: {e.code}, Message: {e.message}",
            extra={
                "request_id": request_id,
                "error_code": e.code,
                "error_details": e.details,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        error_response = ErrorResponse(
            error={
                "code": e.code,
                "message": e.message,
                "details": e.details
            },
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=e.status_code,
            content=error_response.dict()
        )
        
    except HTTPException as e:
        logger.warning(
            f"HTTP error - Request ID: {request_id}, Status: {e.status_code}, Detail: {e.detail}",
            extra={
                "request_id": request_id,
                "status_code": e.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        # Convert HTTPException to our error format
        error_response = ErrorResponse(
            error={
                "code": f"HTTP_{e.status_code}",
                "message": e.detail,
                "details": {}
            },
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=e.status_code,
            content=error_response.dict()
        )
        
    except Exception as e:
        logger.error(
            f"Unexpected error - Request ID: {request_id}, Error: {str(e)}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        error_response = ErrorResponse(
            error={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {"error_type": type(e).__name__}
            },
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.dict()
        )