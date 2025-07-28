# DocuSync Backend

FastAPI-based backend service for the DocuSync documentation maintenance system.

## Features

- **REST API**: Complete REST API for repository management, feedback processing, and analytics
- **Authentication**: Supabase JWT-based authentication
- **GitHub Integration**: Webhook handling and GitHub API integration
- **Workflow Orchestration**: Orkes-based workflow management
- **Real-time Updates**: Server-sent events for live dashboard updates
- **Rate Limiting**: Built-in rate limiting and security middleware
- **Analytics**: Comprehensive analytics and reporting endpoints

## Quick Start

### Prerequisites

- Python 3.11+
- Redis (for rate limiting)
- Supabase account
- GitHub App
- Orkes account
- Google AI API key

### Installation

1. **Clone and setup**:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Start the server**:
   ```bash
   ./start.sh
   ```

   Or manually:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Docker Setup

1. **Using Docker Compose** (recommended):
   ```bash
   docker-compose up -d
   ```

2. **Build and run manually**:
   ```bash
   docker build -t docusync-backend .
   docker run -p 8000:8000 --env-file .env docusync-backend
   ```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Required Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SECRET_KEY=your-secret-key-generate-a-secure-one
GITHUB_WEBHOOK_SECRET=your-webhook-secret
ORKES_API_KEY=your-orkes-api-key
GOOGLE_API_KEY=your-google-ai-api-key

# Optional Configuration
DEBUG=false
REDIS_URL=redis://localhost:6379
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### Supabase Setup

The backend expects the following database tables (see CLAUDE.md for complete schema):

- `users` - User accounts and preferences
- `repositories` - Monitored repositories
- `doc_feedback` - Documentation feedback and suggestions
- `workflow_logs` - Workflow execution logs

### GitHub App Setup

1. Create a GitHub App in your GitHub settings
2. Set webhook URL to: `https://your-domain.com/webhooks/github`
3. Required permissions:
   - Contents: Read & Write
   - Pull requests: Read & Write
   - Issues: Read
4. Subscribe to events:
   - Push
   - Pull request
   - Issues

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

#### Repository Management
- `GET /api/v1/repositories` - List user repositories
- `POST /api/v1/repositories` - Add repository
- `PUT /api/v1/repositories/{id}/config` - Update configuration
- `DELETE /api/v1/repositories/{id}` - Remove repository

#### Feedback Management
- `GET /api/v1/feedback` - List feedback items
- `POST /api/v1/feedback/submit` - Submit feedback
- `POST /api/v1/feedback/{id}/approve` - Approve suggestion
- `POST /api/v1/feedback/{id}/reject` - Reject suggestion

#### Workflows & Analytics
- `GET /api/v1/workflows` - List workflow executions
- `GET /api/v1/analytics/dashboard` - Get dashboard analytics
- `GET /api/v1/analytics/repositories/{id}/metrics` - Repository metrics

#### User Management
- `GET /api/v1/user/profile` - Get user profile
- `PUT /api/v1/user/preferences` - Update preferences

#### Webhooks
- `POST /webhooks/github` - GitHub webhook endpoint

## Architecture

### Directory Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Configuration
│   ├── middleware/      # Auth, rate limiting, error handling
│   ├── models/          # Pydantic models
│   └── services/        # External service integrations
├── logs/                # Application logs
├── main.py             # FastAPI application
├── requirements.txt    # Dependencies
├── Dockerfile         # Container configuration
└── docker-compose.yml # Multi-service setup
```

### Key Components

1. **FastAPI Application** (`main.py`)
   - Main application with middleware and route configuration
   - CORS, error handling, rate limiting

2. **Authentication Middleware** (`middleware/auth.py`)
   - Supabase JWT token verification
   - User session management

3. **Service Layer** (`services/`)
   - `SupabaseService`: Database operations
   - `GitHubService`: GitHub API integration
   - `OrkesService`: Workflow orchestration
   - `NotificationService`: Slack/email notifications

4. **API Routes** (`api/v1/`)
   - RESTful endpoints for all functionality
   - Proper error handling and validation

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

### Adding New Endpoints

1. Create route in appropriate `api/v1/` module
2. Add Pydantic models in `models/`
3. Implement business logic in `services/`
4. Add error handling
5. Update tests

## Deployment

### Production Considerations

1. **Environment**:
   - Set `DEBUG=false`
   - Use strong `SECRET_KEY`
   - Configure proper CORS origins

2. **Database**:
   - Use connection pooling
   - Set up read replicas if needed

3. **Caching**:
   - Redis for rate limiting and sessions
   - Consider CDN for static content

4. **Monitoring**:
   - Set up log aggregation
   - Configure health checks
   - Monitor rate limits and errors

5. **Security**:
   - Use HTTPS everywhere
   - Implement proper CORS policies
   - Regular security updates

### Docker Production Setup

```bash
# Production docker-compose
docker-compose -f docker-compose.yml --profile production up -d
```

This includes:
- Nginx reverse proxy
- SSL termination
- Rate limiting
- Log collection

## Monitoring & Logs

### Log Files

- `logs/docusync.log` - Application logs
- `logs/errors.log` - Error logs (JSON format)
- `logs/access.log` - HTTP access logs

### Health Checks

- `GET /health` - Basic health check
- `GET /webhooks/github/status` - GitHub integration status

### Metrics

The application exposes metrics for monitoring:
- Request rates and response times
- Error rates by endpoint
- Workflow execution metrics
- Authentication success/failure rates

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Check Supabase configuration
   - Verify JWT token format
   - Ensure service role key permissions

2. **GitHub Webhook Issues**:
   - Verify webhook secret
   - Check endpoint accessibility
   - Review webhook delivery logs in GitHub

3. **Workflow Failures**:
   - Check Orkes service status
   - Verify API key and permissions
   - Review workflow execution logs

4. **Rate Limiting**:
   - Check Redis connection
   - Review rate limit configuration
   - Monitor request patterns

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true uvicorn main:app --reload --log-level debug
```

## Support

For issues and questions:
1. Check the logs in `logs/` directory
2. Review API documentation at `/docs`
3. Verify environment configuration
4. Check external service status (Supabase, GitHub, Orkes)