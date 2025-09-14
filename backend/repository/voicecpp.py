import os, re, uuid, subprocess
import soundfile as sf  # <-- for direct wav writing
import shutil

from schema.sound import UPLOAD_FOLDER

class VoiceRepositoryCpp:
    def __init__(self):
        base_path = r"D:\development\stt\backend"
        self.model_path = r"D:\development\stt\voice_model\whisper.cpp\models\ggml-base.en.bin"
        self.exe_path = r"D:\development\stt\voice_model\whisper.cpp\bin\release\whisper-cli.exe"

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        if not os.path.exists(self.exe_path):
            raise FileNotFoundError(f"Executable not found: {self.exe_path}")

        self.base_path = base_path

    def transcribe_voice(self, file: bytes):
        """
        Save raw PCM16 (16kHz mono) to wav and run whisper.cpp CLI.
        """
        # unique_name = f"{uuid.uuid4().hex}.wav"
        # wav_file = os.path.join(UPLOAD_FOLDER, current_user_sub, unique_name)
        # os.makedirs(os.path.dirname(wav_file), exist_ok=True)

        # if isinstance(file, (bytes, bytearray)):
        #     # Convert PCM16 buffer -> wav directly
        #     import numpy as np
        #     arr = np.frombuffer(file, dtype=np.int16)
        #     sf.write(wav_file, arr, 16000, subtype="PCM_16")
        # elif isinstance(file, str) and os.path.exists(file):  # already a path
        #     shutil.copy(file, wav_file)
        # else:
        #     raise ValueError("Unsupported file type for transcribe_voice")

        # Call whisper.cpp directly
        subp_result = subprocess.run(
            [
                self.exe_path,
                "-m", self.model_path,
                "-f", os.path.join(self.base_path, file),
                "--language", "en"
            ],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.join(self.base_path, file))
        )

        if subp_result.returncode == 0:
            transcription = subp_result.stdout.strip()
            if transcription:
                
                clean_text = re.sub(r'\[.*?\]\s*', '', transcription).strip()
                return clean_text, True
            else:
                return "No transcription found", False
        else:
            return f"Transcription failed: {subp_result.stderr}", False
