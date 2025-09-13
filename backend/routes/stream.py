# routes/stream.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import numpy as np, soundfile as sf, tempfile, os
from repository.voicecpp import VoiceRepositoryCpp

router = APIRouter(prefix="/stream", tags=["stream"])

@router.websocket("/voicein")
async def voicein(ws: WebSocket):
    await ws.accept()
    print("Voice WebSocket connected ✅")

    speech_buffer = bytearray()

    try:
        while True:
            msg = await ws.receive_bytes()  # direct PCM
            print(f"Got PCM chunk: {len(msg)} bytes")
            speech_buffer.extend(msg)

            # 👇 Example: simple buffer flush on size threshold
            if len(speech_buffer) > 16000 * 2 * 3:  # ~3 seconds of audio
                arr = np.frombuffer(speech_buffer, dtype=np.int16)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    sf.write(tf.name, arr, 16000, subtype="PCM_16")
                    tmp_wav = tf.name

                # run your transcriber
                voice = VoiceRepositoryCpp()
                transcribed_text, _ = await voice.transcribe_voice(tmp_wav, "testuser")
                await ws.send_text(f"TRANSCRIPT::{transcribed_text}")
                await ws.send_text(f"AI_RESPONSE::I heard {transcribed_text}")

                os.remove(tmp_wav)
                speech_buffer = bytearray()  # reset

    except WebSocketDisconnect:
        print("Voice WebSocket disconnected ❌")
