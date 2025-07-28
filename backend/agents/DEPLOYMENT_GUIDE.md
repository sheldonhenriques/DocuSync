# 🚀 DocuSync Deployment Guide

## Complete Workflow: webhook → get diff → send to LLM → get summary → post to GitHub

This guide shows you how to deploy the complete DocuSync system with webhook server integration.

## 🎯 **Two Deployment Options**

### Option 1: Webhook Server (Recommended for Testing)
**Receives webhooks directly and processes them immediately**

```bash
python webhook_server_integrated.py
```

- **Port**: 5000 (configurable via `WEBHOOK_PORT` env var)
- **Endpoints**: 
  - `POST /webhook` - GitHub webhook receiver
  - `GET /health` - Health check
  - `GET /status` - Detailed status
  - `GET /` - Info page
- **Processing**: Immediate webhook processing with AI analysis

### Option 2: Orkes Orchestrated (Production)
**Uses Orkes workflows for enterprise orchestration**

```bash
python main.py
```

- **Mode**: Connects to Orkes Cloud
- **Workflows**: Registers workflows for orchestration
- **Agents**: Polls Orkes for tasks
- **Scalability**: Enterprise-ready with Orkes orchestration

## 📡 **Webhook Server Details**

### **Port Configuration**
The webhook server runs on **port 5000** by default. You can change this:

```bash
# In your backend/.env file
WEBHOOK_PORT=8080
```

Or set environment variable:
```bash
WEBHOOK_PORT=8080 python webhook_server_integrated.py
```

### **Webhook URL Structure**
- **Local development**: `http://localhost:5000/webhook`  
- **Production**: `https://your-domain.com/webhook`
- **Codespace**: `https://your-codespace-url-5000.app.github.dev/webhook`

## ⚙️ **GitHub Webhook Configuration**

### 1. Go to Repository Settings
Navigate to: `https://github.com/your-username/your-repo/settings/hooks`

### 2. Add Webhook
- **Payload URL**: `https://your-domain.com/webhook`
- **Content type**: `application/json`
- **Secret**: `bahen` (or your custom secret from `.env`)
- **Events**: Select "Pull requests"
- **Active**: ✅ Checked

### 3. Test Configuration
The webhook server provides a status endpoint to verify setup:
```bash
curl http://localhost:5000/status
```

## 🔄 **Complete Workflow Process**

When a PR is opened/updated, here's what happens:

```
1. 📨 GitHub sends webhook → http://your-server:5000/webhook
2. 🔍 Server validates signature and extracts PR data  
3. 📥 Fetches actual PR diff from GitHub API
4. 🤖 Processes through DocuSync agents:
   - CommitWatcherAgent analyzes changes
   - Determines documentation requirements
   - Generates AI-powered insights
5. 💬 GitHubBotAgent posts intelligent comment to PR
6. ✅ Developers see AI analysis on their PR
```

## 🛠️ **Environment Configuration**

Required in `/workspaces/DocuSync/backend/.env`:

```bash
# GitHub Integration
GITHUB_TOKEN=your_github_pat_token
GITHUB_WEBHOOK_SECRET=bahen

# Webhook Server
WEBHOOK_PORT=5000

# Orkes (Optional - for Option 2)
ORKES_API_KEY=your_orkes_api_key  
ORKES_SERVER_URL=https://developer.orkescloud.com/api

# Google AI (Future LLM integration)
GOOGLE_API_KEY=your_google_api_key
```

## 🧪 **Testing the Complete Workflow**

### 1. Test Individual Components
```bash
# Test PR analysis only
python simple_test.py

# Test complete workflow simulation
python final_test.py  

# Test actual GitHub comment posting
python test_pr_comment.py
```

### 2. Test Webhook Server
```bash
# Start the server
python webhook_server_integrated.py

# In another terminal, simulate webhook
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d '{"action":"opened","pull_request":{"number":1,"title":"Test PR"},"repository":{"full_name":"test/repo"}}'
```

### 3. Test with Real GitHub Webhook
1. Start webhook server: `python webhook_server_integrated.py`
2. Use a tool like [ngrok](https://ngrok.com/) to expose local server: `ngrok http 5000`
3. Configure GitHub webhook with ngrok URL: `https://xyz.ngrok.io/webhook`
4. Open a PR in your repository
5. Watch the server logs and check for AI comment on your PR

## 🚀 **Production Deployment**

### Option A: Simple Server Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Set production environment variables
export WEBHOOK_PORT=80
export FLASK_ENV=production

# Run with production WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:80 webhook_server_integrated:app
```

### Option B: Docker Deployment  
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "webhook_server_integrated.py"]
```

### Option C: Cloud Deployment (Recommended)
Deploy to services like:
- **Heroku**: Easy deployment with automatic HTTPS
- **Railway**: Simple Python app hosting  
- **Google Cloud Run**: Serverless container deployment
- **AWS Lambda**: Serverless webhook processing

## 📊 **Monitoring & Health Checks**

### Health Check Endpoint
```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-26T10:30:00Z",
  "agents_initialized": true,
  "github_token_configured": true,
  "webhook_secret_configured": true
}
```

### Status Endpoint
```bash
curl http://localhost:5000/status
```

Provides detailed system status including agent initialization and configuration.

## 🔧 **Troubleshooting**

### Common Issues

1. **Webhook not received**
   - Check GitHub webhook configuration
   - Verify webhook URL is accessible
   - Check webhook secret matches

2. **Agents not initialized**
   - Verify `GITHUB_TOKEN` is set
   - Check agent logs for initialization errors

3. **Comments not posting**
   - Verify GitHub token has PR comment permissions
   - Check rate limiting on GitHub API
   - Review bot agent logs

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python webhook_server_integrated.py
```

## 🎉 **Success Verification**

You'll know everything is working when:

1. ✅ Webhook server starts without errors
2. ✅ Status endpoint shows all components healthy  
3. ✅ Opening a PR triggers webhook processing
4. ✅ AI-generated comment appears on the PR
5. ✅ Comment includes technical analysis and documentation insights

## 📝 **Next Steps**

1. **Configure GitHub webhooks** for your repositories
2. **Test with real PRs** to verify end-to-end functionality
3. **Customize AI responses** by modifying the comment generation logic
4. **Scale up** with Orkes workflows for multiple repositories
5. **Monitor and optimize** based on usage patterns

---

🤖 **The webhook server at port 5000 is your complete solution for**: 
**webhook → get diff → send to LLM → get summary → post to GitHub** ✨