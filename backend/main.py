from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

from app.core.config import settings
from app.middleware.error_handler import error_handler_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.api.v1 import repositories, feedback, workflows, analytics, users, webhooks, github

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="AI-powered documentation maintenance system"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.middleware("http")(error_handler_middleware)
app.middleware("http")(rate_limit_middleware)

# API Routes
app.include_router(repositories.router, prefix=settings.api_v1_prefix, tags=["repositories"])
app.include_router(feedback.router, prefix=settings.api_v1_prefix, tags=["feedback"])
app.include_router(workflows.router, prefix=settings.api_v1_prefix, tags=["workflows"])
app.include_router(analytics.router, prefix=settings.api_v1_prefix, tags=["analytics"])
app.include_router(users.router, prefix=settings.api_v1_prefix, tags=["users"])
app.include_router(github.router, prefix=settings.api_v1_prefix, tags=["github"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docusync-backend"}

@app.get("/api/test")
async def api_test():
    return {
        "status": "API connection successful",
        "timestamp": "2025-01-26T12:00:00Z",
        "endpoints": [
            "/api/v1/repositories",
            "/api/v1/feedback", 
            "/api/v1/workflows",
            "/api/v1/analytics",
            "/api/v1/users"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )