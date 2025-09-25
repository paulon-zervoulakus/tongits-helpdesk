from fastapi import status
from utils.authentication import verify_jwt_token, AuthUser

# Expects token in query params: ws://.../voicein?token=xxx
async def validate_access_token(token: str):
    if not token:        
        return False, status.HTTP_204_NO_CONTENT
    try:
        user_data = verify_jwt_token(token)
        user = AuthUser(user_data)
    except Exception:
        return False, status.WS_1008_POLICY_VIOLATION
        
    # Pass user to endpoint
    return True, user
