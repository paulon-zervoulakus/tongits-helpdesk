""" Authentication Utils """
import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv(dotenv_path=os.path.abspath("./frontend/.env/"))

# Get this from your environment variables
GOOGLE_CLIENT_ID = os.getenv('VITE_GOOGLE_CLIENT_ID')
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zzz")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()

class AuthUser:
    def __init__(self, user_data: Dict[str, Any]):
        self.email = user_data.get("email")
        self.name = user_data.get("name")
        self.picture = user_data.get("picture")
        self.sub = user_data.get("sub")  # Google user ID

    def to_dict(self):
        return {
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "sub": self.sub
        }

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def verify_google_token(token: str) -> Dict[str, Any]:
    """Verify Google OAuth token and return user info"""
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )

        # Additional verification
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        return idinfo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthUser:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    
    try:
        # Try to verify as JWT token first (for subsequent requests)
        user_data = verify_jwt_token(token)
        return AuthUser(user_data)
    except HTTPException:
        # If JWT verification fails, try Google token verification (for initial auth)
        try:
            google_user_data = verify_google_token(token)
            return AuthUser(google_user_data)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

def create_jwt_token(user_data: Dict[str, Any]) -> str:
    """Create JWT token from user data"""
    payload = {
        "sub": user_data["sub"],
        "email": user_data["email"],
        "name": user_data["name"],
        "picture": user_data["picture"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
