""" Authentication routes"""
from utils.authentication import AuthUser, get_current_user, verify_google_token, create_jwt_token
from fastapi import APIRouter, Depends, HTTPException, status
from schema.auth import (
    GoogleAuthRequestSchema,
    AuthResponseSchema,
    AuthResponseDataSchema,
    TokenVerifyResponseSchema,
    TokenRefreshResponseSchema
)
from schema.user import UserSchema
from repository.user  import UserRepository
from database import get_db
from sqlalchemy.orm import Session
router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/google")
async def google_auth(
    auth_request: GoogleAuthRequestSchema,
    db: Session = Depends(get_db)
):
    """Google OAuth authentication"""
    try:
        # Get the token from the request body
        token = auth_request.credential

        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No token available"
            )

        # Verify the token with Google
        user_info = verify_google_token(token)
        
        # Extract user details
        user_id = user_info['sub']
        email = user_info['email']
        name = user_info['name']
        picture = user_info.get('picture')

        user_repository = UserRepository(db)
        user = user_repository.find_by_google_id(user_id)

        if not user:
            # Create a new user if not found
            user_data = {
                "google_id": user_id,
                "email": email,
                "name": name,
                "picture": picture
            }
            user = user_repository.create(user_data)
        else:
            # Update existing user information if needed
            user_repository.update(user, {
                "name": name,
                "picture": picture
            })

        # Create a JWT token
        session_token = create_jwt_token(user.to_dict())

        # Return the user info and token
        return AuthResponseSchema(
            status="success",
            message="User authenticated",
            data=AuthResponseDataSchema(
                access_token=session_token,
                user=UserSchema(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    picture=user.picture
                )
            )
        )


    except ValueError:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    except Exception as e:
        # Other errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/verify", response_model=TokenVerifyResponseSchema)
async def verify_token(current_user: AuthUser = Depends(get_current_user)):
    """Verify current token and return user info"""
    return TokenVerifyResponseSchema(
        user=current_user.to_dict(), 
        valid=True
    )

@router.post("/refresh", response_model=TokenRefreshResponseSchema)
async def refresh_token(current_user: AuthUser = Depends(get_current_user)):
    """Refresh JWT token"""
    new_token = create_jwt_token(current_user.to_dict())
    return TokenRefreshResponseSchema(
        access_token=new_token, 
        token_type="bearer"
    )