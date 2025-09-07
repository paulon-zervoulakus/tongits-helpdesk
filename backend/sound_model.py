""" Sound model """

from faster_whisper import WhisperModel

from whispercpp import Whisper

# Load model once at startup (CPU mode for now)
model = WhisperModel("medium", device="cpu", compute_type="float32")  

modelcpp = Whisper.from_pretrained("small.en")
