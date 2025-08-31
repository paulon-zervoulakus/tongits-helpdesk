from pydantic import BaseModel
from typing import (Optional, Dict, Any)
from schema.user import UserSchema

class AuthResponseDataSchema(BaseModel):
    access_token: str
    user: UserSchema

class AuthResponseSchema(BaseModel):
    status: str
    message: str
    data: AuthResponseDataSchema

class GoogleAuthRequestSchema(BaseModel):
    credential: Optional[str] = None

class TokenVerifyResponseSchema(BaseModel):
    user: Dict[str, Any]
    valid: bool

class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str