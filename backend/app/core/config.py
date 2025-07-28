from pydantic_settings import BaseSettings
from typing import Optional
import os
import base64


class Settings(BaseSettings):
    # API Configuration
    app_name: str = "DocuSync API"
    app_version: str = "1.0.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    
    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    
    # GitHub Configuration
    github_app_id: str
    github_private_key: str
    github_webhook_secret: str
    github_token: Optional[str] = None
    
    @property
    def github_private_key_decoded(self) -> str:
        """Get the GitHub private key, handling base64 encoding if needed"""
        try:
            # Check if the key looks like it's base64 encoded (no PEM headers)
            if not self.github_private_key.startswith('-----BEGIN'):
                # Try to decode as base64
                decoded = base64.b64decode(self.github_private_key).decode('utf-8')
                return decoded
            else:
                # Already in PEM format, return as-is
                return self.github_private_key
        except Exception as e:
            print(f"Error decoding GitHub private key: {e}")
            # Return as-is if decoding fails
            return self.github_private_key
    
    # Orkes Configuration
    orkes_api_key: str
    orkes_server_url: str = "https://play.orkes.io/api"
    
    # Google AI Configuration
    google_api_key: str
    
    # Daytona Configuration (optional for advanced validation)
    daytona_api_key: Optional[str] = None
    daytona_base_url: Optional[str] = "https://api.daytona.io"
    
    # Redis Configuration (for rate limiting)
    redis_url: str = "redis://localhost:6379"
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Webhook Configuration
    webhook_timeout: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()