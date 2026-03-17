import os
import httpx
import logging
from typing import Optional
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Config
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
CLERK_API_KEY = os.getenv("CLERK_API_KEY")

security = HTTPBearer()

class ClerkUser(BaseModel):
    user_id: str
    email: Optional[str] = None
    claims: dict

class ClerkAuth:
    _jwks: Optional[dict] = None

    @classmethod
    async def get_jwks(cls):
        if cls._jwks is None:
            if not CLERK_JWKS_URL:
                raise ValueError("CLERK_JWKS_URL environment variable is not set")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(CLERK_JWKS_URL)
                response.raise_for_status()
                cls._jwks = response.json()
        return cls._jwks

    @classmethod
    async def verify_token(cls, token: str) -> ClerkUser:
        try:
            jwks = await cls.get_jwks()
            
            # Extract header to find kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise HTTPException(status_code=401, detail="Header missing kid")

            # Find matching key
            rsa_key = {}
            for key in jwks.get("keys", []):
                if key["kid"] == kid:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
                    break
            
            if not rsa_key:
                raise HTTPException(status_code=401, detail="Invalid key identifier")

            # Decode and verify
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                options={"verify_at_hash": False}
            )
            
            return ClerkUser(
                user_id=payload.get("sub"),
                email=payload.get("email"),
                claims=payload
            )
        except JWTError as e:
            logger.error(f"JWT Verification failed: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication server error")

async def get_current_user(auth: HTTPAuthorizationCredentials = Security(security)) -> ClerkUser:
    """Dependency to be used in FastAPI routes"""
    return await ClerkAuth.verify_token(auth.credentials)
