""" This is a shema for sound files """
import os

# Folder for uploaded audio
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

UPLOAD_TEMP_FOLDER = "temp"
os.makedirs(UPLOAD_TEMP_FOLDER, exist_ok=True)


VOICE_MODEL_PATH = r"D:\development\stt\voice_model\piper-stt\models\en\en_US-amy-medium.onnx"
VOICE_CONFIG_PATH = r"D:\development\stt\voice_model\piper-stt\models\en\en_US-amy-medium.onnx.json"
