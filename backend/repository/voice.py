import os
import io
import uuid
from fastapi import UploadFile
from schema.sound import UPLOAD_FOLDER
from sound_model import model as sound_model

class VoiceRepository:
    def __init__(self):
        pass

    async def save_voice(self, file: UploadFile, current_user_sub: str):
        """ This repositor will save the voice chat and return a Transcribe text
            Params:
                file: The uploaded file
                current_user_sub: Google ID
                save_file: to save or not
        """       
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[-1]
        unique_name = f"{uuid.uuid4().hex}{file_ext}"
        audio = os.path.join(UPLOAD_FOLDER, current_user_sub, unique_name)

        os.makedirs(os.path.dirname(audio), exist_ok=True)
        # Save file
        with open(audio, "wb") as f:
            f.write(await file.read())       

        # Run transcription
        segments, _ = sound_model.transcribe(audio)
        
        # Concatenate text
        text = " ".join([segment.text for segment in segments])

        return text, unique_name