from fastapi import Request, HTTPException, status
from typing import Dict, Optional
import time
import redis
import json
from collections import defaultdict

from app.core.config import settings

# In-memory rate limiter for development (use Redis in production)
class InMemoryRateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict[str, int]]:
        now = time.time()
        window_start = now - window
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        
        # Check if limit exceeded
        current_requests = len(self.requests[key])
        if current_requests >= limit:
            remaining = 0
            reset_time = int(self.requests[key][0] + window)
        else:
            # Add current request
            self.requests[key].append(now)
            remaining = limit - (current_requests + 1)
            reset_time = int(now + window)
        
        headers = {
            "X-RateLimit-Limit": limit,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Reset": reset_time,
            "X-RateLimit-Window": window
        }
        
        return current_requests < limit, headers


class RedisRateLimiter:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict[str, int]]:
        try:
            pipe = self.redis.pipeline()
            now = time.time()
            window_start = now - window
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_requests = results[1]
            
            remaining = max(0, limit - current_requests - 1)
            reset_time = int(now + window)
            
            headers = {
                "X-RateLimit-Limit": limit,
                "X-RateLimit-Remaining": remaining,
                "X-RateLimit-Reset": reset_time,
                "X-RateLimit-Window": window
            }
            
            return current_requests < limit, headers
            
        except Exception as e:
            # Fallback to allow request if Redis fails
            print(f"Rate limiter error: {e}")
            return True, {}


# Initialize rate limiter
try:
    rate_limiter = RedisRateLimiter(settings.redis_url)
except:
    rate_limiter = InMemoryRateLimiter()


def get_rate_limit_key(request: Request) -> str:
    """Generate rate limit key based on user or IP"""
    # Try to get user ID from auth header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            # In a real implementation, you'd decode the JWT to get user ID
            # For now, use the token as key (hashed for privacy)
            import hashlib
            token_hash = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
            return f"user:{token_hash}"
        except:
            pass
    
    # Fallback to IP address
    client_ip = request.client.host
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    return f"ip:{client_ip}"


def get_endpoint_limits(path: str, method: str) -> tuple[int, int]:
    """Get rate limits for specific endpoints"""
    # Different limits for different endpoint types
    if path.startswith("/api/v1/feedback/submit"):
        return 10, 60  # 10 requests per minute for feedback submission
    elif method in ["POST", "PUT", "DELETE"]:
        return 30, 60  # 30 requests per minute for write operations
    else:
        return 100, 60  # 100 requests per minute for read operations


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for health checks and internal endpoints
    if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
        response = await call_next(request)
        return response
    
    # Get rate limit parameters
    key = get_rate_limit_key(request)
    limit, window = get_endpoint_limits(request.url.path, request.method)
    
    # Check rate limit
    allowed, headers = rate_limiter.is_allowed(key, limit, window)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers=headers
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    for header_name, header_value in headers.items():
        response.headers[header_name] = str(header_value)
    
    return response