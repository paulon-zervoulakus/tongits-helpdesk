import os
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, FileResponse
from utils.authentication import AuthUser, get_current_user
from schema.sound import UPLOAD_FOLDER

router = APIRouter(prefix="/audio", tags=["chat"])

@router.get("/{filename}")
async def get_audio(
    filename: str,
    current_user: AuthUser = Depends(get_current_user)
):    
    user_path = current_user.sub
    file_path = os.path.join(UPLOAD_FOLDER, user_path, filename)
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(file_path, media_type="audio/wav")

