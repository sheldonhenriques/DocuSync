from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any]
    request_id: Optional[str] = None


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class PaginationResponse(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int