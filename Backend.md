# DocuSync Backend APIs & Data Structures

## API Architecture Overview

### Base URL Structure
```
Production: https://api.docusync.dev
Development: http://localhost:8000
```

### Authentication
- **Method**: Supabase JWT tokens
- **Header**: `Authorization: Bearer <supabase_jwt_token>`
- **Flow**: Frontend gets token from Supabase Auth, passes to backend APIs

---

## Core API Endpoints

### 1. Repository Management APIs

#### `GET /api/v1/repositories`
**Purpose**: Get all repositories for authenticated user

**Request Headers**:
```json
{
  "Authorization": "Bearer <jwt_token>",
  "Content-Type": "application/json"
}
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-string",
      "github_repo_id": 12345,
      "repo_name": "mycompany/awesome-api",
      "owner": "mycompany",
      "full_name": "mycompany/awesome-api",
      "doc_config": {
        "watch_patterns": ["*.py", "*.md", "api/**"],
        "ignore_patterns": ["node_modules/**", "*.pyc"],
        "doc_root": "docs/",
        "auto_approve": false,
        "notification_settings": {
          "slack_webhook": "https://hooks.slack.com/...",
          "email_notifications": true
        }
      },
      "status": "active", // active, paused, error
      "last_sync": "2025-07-26T10:30:00Z",
      "stats": {
        "total_docs": 45,
        "pending_updates": 3,
        "last_workflow_run": "2025-07-26T09:15:00Z"
      },
      "created_at": "2025-07-01T00:00:00Z",
      "updated_at": "2025-07-26T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

#### `POST /api/v1/repositories`
**Purpose**: Add new repository to DocuSync monitoring

**Request Body**:
```json
{
  "github_repo_url": "https://github.com/mycompany/awesome-api",
  "doc_config": {
    "watch_patterns": ["*.py", "*.md", "api/**"],
    "ignore_patterns": ["node_modules/**"],
    "doc_root": "docs/",
    "auto_approve": false
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "repo_name": "mycompany/awesome-api",
    "status": "active",
    "webhook_installed": true,
    "initial_scan_triggered": true
  },
  "message": "Repository added successfully. Initial documentation scan started."
}
```

#### `PUT /api/v1/repositories/{repo_id}/config`
**Purpose**: Update repository configuration

**Request Body**:
```json
{
  "doc_config": {
    "watch_patterns": ["*.py", "*.md", "api/**", "src/**"],
    "auto_approve": true,
    "notification_settings": {
      "slack_webhook": "https://hooks.slack.com/new-webhook"
    }
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "doc_config": { /* updated config */ },
    "updated_at": "2025-07-26T11:00:00Z"
  }
}
```

---

### 2. Documentation Feedback APIs

#### `GET /api/v1/feedback`
**Purpose**: Get pending documentation feedback/suggestions

**Query Parameters**:
- `status` (optional): `pending`, `approved`, `rejected`, `all`
- `repo_id` (optional): Filter by repository
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-string",
      "repo_id": "uuid-string",
      "repo_name": "mycompany/awesome-api",
      "file_path": "docs/api/authentication.md",
      "section": "OAuth Flow",
      "feedback_type": "user_confusion", // user_confusion, code_change, validation_error
      "feedback_text": "The OAuth callback URL configuration is unclear. Where exactly do I set this?",
      "suggestion": "# OAuth Callback Configuration\n\nTo configure your OAuth callback URL:\n\n1. Navigate to your app settings...",
      "validation_results": {
        "code_examples": {
          "valid": true,
          "blocks_tested": 2,
          "daytona_workspace_url": "https://workspace-def456.daytona.io",
          "execution_times_ms": [1240, 890]
        },
        "links_valid": true,
        "formatting_valid": true
      },
      "confidence_score": 0.87,
      "priority": "medium", // high, medium, low
      "status": "pending",
      "triggered_by": {
        "type": "user_feedback", // user_feedback, code_change, pr_review
        "user_id": "uuid-string",
        "event_id": "github-event-id"
      },
      "workflow_info": {
        "orkes_workflow_id": "workflow-uuid",
        "orkes_execution_id": "execution-uuid",
        "agent_responses": [
          {
            "agent": "doc_maintainer",
            "status": "completed",
            "execution_time_ms": 2340
          },
          {
            "agent": "style_checker", 
            "status": "completed",
            "execution_time_ms": 890
          }
        ]
      },
      "created_at": "2025-07-26T09:15:00Z",
      "updated_at": "2025-07-26T09:15:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

#### `POST /api/v1/feedback/{feedback_id}/approve`
**Purpose**: Approve a documentation suggestion

**Request Body**:
```json
{
  "approved_content": "# OAuth Callback Configuration\n\n...", // optional: modified content
  "commit_message": "docs: clarify OAuth callback URL configuration", // optional
  "auto_commit": true // optional: default true
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "feedback_id": "uuid-string",
    "status": "approved",
    "github_commit": {
      "sha": "abc123def456",
      "url": "https://github.com/mycompany/awesome-api/commit/abc123def456",
      "message": "docs: clarify OAuth callback URL configuration"
    },
    "updated_at": "2025-07-26T11:30:00Z"
  }
}
```

#### `POST /api/v1/feedback/{feedback_id}/reject`
**Purpose**: Reject a documentation suggestion

**Request Body**:
```json
{
  "reason": "suggestion_incorrect", // suggestion_incorrect, out_of_scope, duplicate
  "notes": "The OAuth flow described is for our legacy API, not the current v2 API"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "feedback_id": "uuid-string",
    "status": "rejected",
    "rejection_reason": "suggestion_incorrect",
    "updated_at": "2025-07-26T11:30:00Z"
  }
}
```

#### `POST /api/v1/feedback/submit`
**Purpose**: Submit reader feedback from documentation site

**Request Body**:
```json
{
  "repo_id": "uuid-string",
  "file_path": "docs/api/authentication.md",
  "section": "OAuth Flow", // optional
  "feedback_text": "This section is confusing",
  "page_url": "https://docs.mycompany.com/api/authentication#oauth-flow",
  "user_context": { // optional anonymous analytics
    "user_agent": "Mozilla/5.0...",
    "referrer": "https://docs.mycompany.com/api/"
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "feedback_id": "uuid-string",
    "estimated_response_time": "2-5 minutes",
    "workflow_triggered": true,
    "orkes_workflow_id": "workflow-uuid"
  },
  "message": "Thank you for your feedback! Our AI agents are working on an improved explanation."
}
```

---

### 3. Workflow & Analytics APIs

#### `GET /api/v1/workflows`
**Purpose**: Get workflow execution history and status

**Query Parameters**:
- `repo_id` (optional): Filter by repository
- `status` (optional): `running`, `completed`, `failed`, `all`
- `trigger_type` (optional): `pr`, `commit`, `feedback`, `manual`
- `page`, `per_page`: Pagination

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-string",
      "orkes_workflow_id": "workflow-uuid",
      "orkes_execution_id": "execution-uuid",
      "repo_id": "uuid-string",
      "repo_name": "mycompany/awesome-api",
      "trigger_event": {
        "type": "pull_request", // pull_request, push, feedback, manual
        "github_event_id": "12345",
        "pr_number": 42,
        "branch": "feature/update-auth-docs",
        "commit_sha": "abc123def456"
      },
      "status": "completed", // running, completed, failed, cancelled
      "progress": {
        "current_step": "github_bot",
        "total_steps": 5,
        "completed_steps": 5
      },
      "agents_executed": [
        {
          "agent_name": "commit_watcher",
          "status": "completed",
          "execution_time_ms": 1250,
          "output_summary": "Found 3 relevant file changes",
          "started_at": "2025-07-26T09:00:00Z",
          "completed_at": "2025-07-26T09:00:01Z"
        },
        {
          "agent_name": "validator",
          "status": "completed",
          "execution_time_ms": 15420,
          "output_summary": "Validated 3 code blocks using Daytona",
          "daytona_workspace_url": "https://workspace-abc123.daytona.io",
          "started_at": "2025-07-26T09:00:05Z",
          "completed_at": "2025-07-26T09:00:20Z"
        }
      ],
      "results": {
        "docs_updated": 2,
        "validation_passed": true,
        "github_comment_posted": true,
        "feedback_items_created": 1
      },
      "execution_time_total_ms": 8950,
      "started_at": "2025-07-26T09:00:00Z",
      "completed_at": "2025-07-26T09:00:09Z"
    }
  ]
}
```

#### `GET /api/v1/analytics/dashboard`
**Purpose**: Get dashboard analytics and metrics

**Query Parameters**:
- `repo_id` (optional): Filter by repository
- `timeframe`: `24h`, `7d`, `30d`, `90d`

**Response**:
```json
{
  "success": true,
  "data": {
    "timeframe": "7d",
    "overview": {
      "total_workflows": 45,
      "successful_workflows": 42,
      "failed_workflows": 3,
      "success_rate": 93.3,
      "avg_execution_time_ms": 6750,
      "docs_updated": 127,
      "feedback_processed": 23
    },
    "daily_stats": [
      {
        "date": "2025-07-26",
        "workflows": 8,
        "docs_updated": 12,
        "feedback_items": 3,
        "avg_execution_time_ms": 5200
      }
    ],
    "repository_breakdown": [
      {
        "repo_id": "uuid-string",
        "repo_name": "mycompany/awesome-api",
        "workflows": 25,
        "docs_updated": 67,
        "success_rate": 96.0
      }
    ],
    "agent_performance": [
      {
        "agent_name": "doc_maintainer",
        "avg_execution_time_ms": 3200,
        "success_rate": 94.5,
        "total_executions": 45
      }
    ],
    "popular_feedback_types": [
      {
        "type": "user_confusion",
        "count": 15,
        "avg_resolution_time_minutes": 12
      }
    ]
  }
}
```

---

### 4. User & Configuration APIs

#### `GET /api/v1/user/profile`
**Purpose**: Get user profile and preferences

**Response**:
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "github_id": 12345,
    "username": "john-doe",
    "email": "john@mycompany.com",
    "avatar_url": "https://github.com/john-doe.png",
    "preferences": {
      "email_notifications": true,
      "slack_notifications": false,
      "auto_approve_low_risk": true,
      "dashboard_refresh_interval": 30
    },
    "subscription": {
      "plan": "pro", // free, pro, enterprise
      "repositories_limit": 10,
      "current_repositories": 3,
      "workflows_per_month_limit": 1000,
      "workflows_this_month": 127
    },
    "created_at": "2025-06-01T00:00:00Z"
  }
}
```

#### `PUT /api/v1/user/preferences`
**Purpose**: Update user preferences

**Request Body**:
```json
{
  "preferences": {
    "email_notifications": false,
    "auto_approve_low_risk": false,
    "dashboard_refresh_interval": 60
  }
}
```

---

### 5. Real-time & Webhook APIs

#### `GET /api/v1/events/stream` (Server-Sent Events)
**Purpose**: Real-time updates for dashboard

**Headers**: 
```
Accept: text/event-stream
Authorization: Bearer <jwt_token>
```

**Event Types**:
```javascript
// Workflow started
data: {
  "type": "workflow_started",
  "workflow_id": "uuid-string",
  "repo_name": "mycompany/awesome-api",
  "trigger": "pull_request"
}

// Workflow completed
data: {
  "type": "workflow_completed", 
  "workflow_id": "uuid-string",
  "status": "completed",
  "results": { "docs_updated": 2 }
}

// New feedback item
data: {
  "type": "feedback_created",
  "feedback_id": "uuid-string",
  "priority": "medium",
  "file_path": "docs/api.md"
}
```

---

## Error Response Format

All APIs return errors in consistent format:

```json
{
  "success": false,
  "error": {
    "code": "REPOSITORY_NOT_FOUND",
    "message": "Repository with ID 'uuid-string' not found",
    "details": {
      "repo_id": "uuid-string",
      "user_id": "uuid-string"
    }
  },
  "request_id": "req_abc123def456" // for debugging
}
```

### Common Error Codes
- `UNAUTHORIZED` (401): Invalid or missing JWT token
- `FORBIDDEN` (403): User doesn't have access to resource
- `NOT_FOUND` (404): Resource doesn't exist
- `VALIDATION_ERROR` (400): Invalid request data
- `RATE_LIMITED` (429): Too many requests
- `WORKFLOW_ERROR` (500): Orkes workflow execution failed
- `GITHUB_API_ERROR` (502): GitHub API integration failed

---

## Rate Limiting

### Limits by Endpoint
- **GET endpoints**: 100 requests/minute per user
- **POST/PUT endpoints**: 30 requests/minute per user  
- **Feedback submission**: 10 requests/minute per IP (anonymous)
- **Webhook endpoints**: 1000 requests/minute (GitHub webhooks)

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1690380000
X-RateLimit-Window: 60
```

---

## Implementation Notes

### Backend Service Structure
```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── repositories.py
│   │   │   ├── feedback.py  
│   │   │   ├── workflows.py
│   │   │   ├── analytics.py
│   │   │   └── users.py
│   │   └── middleware/
│   │       ├── auth.py
│   │       ├── rate_limit.py
│   │       └── error_handler.py
│   ├── services/
│   │   ├── orkes_service.py
│   │   ├── github_service.py
│   │   ├── supabase_service.py
│   │   └── notification_service.py
│   └── models/
│       ├── repository.py
│       ├── feedback.py
│       └── workflow.py
├── requirements.txt
└── main.py
```

### Key Dependencies
```
fastapi>=0.104.0
uvicorn>=0.24.0
supabase>=2.0.0
orkes-conductor-client>=1.0.0
PyGithub>=1.59.0
pydantic>=2.0.0
python-jose>=3.3.0
python-multipart>=0.0.6
redis>=5.0.0  # for rate limiting
```

This API design provides a comprehensive interface for the DocuSync frontend while maintaining clean separation between the dashboard, agent orchestration, and GitHub integration components.