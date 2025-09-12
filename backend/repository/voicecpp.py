import os
import io
import uuid
import subprocess
from fastapi import UploadFile
from schema.sound import UPLOAD_FOLDER
import shutil
# from sound_model import modelcpp as sound_model
import tempfile

class VoiceRepositoryCpp:
    def __init__(self):
        pass

    async def transcribe_voice(self, file: bytes, current_user_sub: str):
        """ This repositor will save the voice chat and return a Transcribe text
            Params:
                file: The uploaded file
                current_user_sub: Google ID
                save_file: to save or not
        """       
        # Generate unique filename
        # file_ext = os.path.splitext(file.filename)[-1]        
        unique_name = f"{uuid.uuid4().hex}.webm"
        webm_file = os.path.join(UPLOAD_FOLDER, current_user_sub, unique_name)

        os.makedirs(os.path.dirname(webm_file), exist_ok=True)
        # Save file
        with open(webm_file, "wb") as f:
            f.write(file)       
        # with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        #     tmp_path = tmp.name
        base_path = r"D:\development\stt\backend"
        # Run transcription
        model_path=r"D:\development\stt\voice_model\whisper.cpp\models\ggml-base.en.bin"
        if not os.path.exists(model_path):
            print(f"Model not found: {exe_path}")
            return "Error: Model not found", unique_name

        exe_path = r"D:\development\stt\voice_model\whisper.cpp\bin\release\whisper-cli.exe"
        if not os.path.exists(exe_path):
            print(f"Executable not found: {exe_path}")
            return "Error: Executable not found", unique_name
        
        wav_file = webm_file.replace('.webm', '.wav')
        subprocess.run([
            r"D:\development\stt\voice_model\ffmpeg\bin\ffmpeg.exe", "-i", webm_file, 
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", 
            wav_file
        ], capture_output=True, text=True)

        subp_result = subprocess.run(
            [
                exe_path,  # binary from release
                "-m", model_path,
                "-f", os.path.join(base_path, wav_file)
            ],            
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.join(base_path, wav_file))
        )

        if subp_result.returncode == 0:
            # Extract just the transcription text, remove timestamps
            transcription = subp_result.stdout.strip()
            if transcription:
                # Remove timestamp format [00:00:00.000 --> 00:00:02.000]
                import re
                clean_text = re.sub(r'\[.*?\]\s*', '', transcription).strip()
                return clean_text, unique_name
            else:
                return "No transcription found", unique_name
        else:
            return f"Transcription failed: {subp_result.stderr}", unique_name