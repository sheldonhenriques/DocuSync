from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from supabase import create_client, Client
from typing import Optional
import httpx

from app.core.config import settings
from app.models.user import User

security = HTTPBearer()

supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)


class AuthenticationError(Exception):
    pass


async def verify_supabase_token(token: str) -> dict:
    """Verify Supabase JWT token and return user data"""
    try:
        # Get Supabase JWT public key
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.supabase_url}/auth/v1/settings")
            if response.status_code != 200:
                raise AuthenticationError("Failed to get Supabase settings")
            
            jwt_settings = response.json()
            jwt_secret = jwt_settings.get("jwt_secret")
            
            if not jwt_secret:
                raise AuthenticationError("JWT secret not found")
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        
        return payload
        
    except JWTError as e:
        raise AuthenticationError(f"Token verification failed: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Authentication error: {str(e)}")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user from Supabase JWT token"""
    try:
        token = credentials.credentials
        payload = await verify_supabase_token(token)
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no user ID found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user data from Supabase
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return response.data[0]
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication service error: {str(e)}"
        )


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires authentication"""
    return user


def optional_auth(user: Optional[dict] = Depends(get_optional_user)) -> Optional[dict]:
    """Dependency for optional authentication"""
    return user