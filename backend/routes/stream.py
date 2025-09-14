# routes/stream.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import numpy as np, soundfile as sf, tempfile, os, traceback
from repository.voicecpp import VoiceRepositoryCpp
import webrtcvad
from collections import deque

router = APIRouter(prefix="/stream", tags=["stream"])

@router.websocket("/voicein")
async def voicein(ws: WebSocket):
    await ws.accept()
    print("Voice WebSocket connected ✅")

    # VAD setup
    vad = webrtcvad.Vad(2)  # 0=least aggressive, 3=most aggressive
    sample_rate = 16000
    frame_ms = 30  # 10, 20, or 30 ms only allowed
    frame_bytes = int(sample_rate * frame_ms / 1000) * 2  # int16=2 bytes

    ring_buffer = deque(maxlen=10)  # short-term buffer to detect speech end
    speech_buffer = bytearray()
    in_speech = False
    silence_threshold = 3
    
    try:
        while True:
            msg = await ws.receive_bytes()  # PCM16 (16kHz, mono)
            speech_buffer.extend(msg)

            # process in fixed-size frames for VAD
            while len(speech_buffer) >= frame_bytes:
                frame = speech_buffer[:frame_bytes]
                speech_buffer = speech_buffer[frame_bytes:]

                is_speech = vad.is_speech(frame, sample_rate) # detech if the frame has speech or silence
                ring_buffer.append((frame, is_speech)) # append a tuple [(F1,true), (F2,false), (F3,true), (F4, true), (F5,false), (F6, true), (F7, false), (F8, true), (F9, false),..]
                
               
                if is_speech and not in_speech:
                    in_speech = True
                    voiced_frames = bytearray()
                    for f, _ in ring_buffer:
                        voiced_frames.extend(f)
                    ring_buffer.clear()

                if in_speech:
                    voiced_frames.extend(frame)
                
                # if silence detected for long enough → end of speech
                if in_speech and sum(1 for _, s in ring_buffer if not s) > silence_threshold:
                    # Save the collected voiced_frames
                    arr = np.frombuffer(voiced_frames, dtype=np.int16)
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                        sf.write(tf.name, arr, sample_rate, subtype="PCM_16")
                        tmp_wav = tf.name   

                    # run transcriber
                    voice = VoiceRepositoryCpp()
                    transcribed_text, _, succeed = await voice.transcribe_voice(tmp_wav, "testuser")
                    if transcribed_text and succeed:
                        await ws.send_text(f"TRANSCRIPT::{transcribed_text}")
                        await ws.send_text(f"AI_RESPONSE::{transcribed_text}")
                    
                    os.remove(tmp_wav)
                    in_speech = False
                    ring_buffer.clear()
                    voiced_frames = bytearray()
                    
    except WebSocketDisconnect:
        print("❌ Client disconnected")
    except Exception as e:
        print("⚠️ Server error:", e)
        traceback.print_exc()
    finally:
        print("🔒 WebSocket closed")
