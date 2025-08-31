""" Sound model """

from faster_whisper import WhisperModel

# Load model once at startup (CPU mode for now)
model = WhisperModel("medium", device="cpu", compute_type="float32")  

