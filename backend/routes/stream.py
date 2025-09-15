# routes/stream.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import numpy as np, soundfile as sf, tempfile, os, traceback, json
from repository.voicecpp import VoiceRepositoryCpp
import webrtcvad, asyncio
from collections import deque
from schema.sound import UPLOAD_TEMP_FOLDER, VOICE_MODEL_PATH, VOICE_CONFIG_PATH
from piper.voice import PiperVoice

router = APIRouter(prefix="/stream", tags=["stream"])
voice = VoiceRepositoryCpp()
tts = PiperVoice.load(VOICE_MODEL_PATH, VOICE_CONFIG_PATH)

async def process_speech(voiced_frames: bytearray, sample_rate: int, ws: WebSocket):
    """Run transcription in a separate thread and send results back"""
    try:

        # Save the collected voiced_frames
        arr = np.frombuffer(voiced_frames, dtype=np.int16)
        with tempfile.NamedTemporaryFile(
            suffix=".wav", 
            delete=False,
            dir=UPLOAD_TEMP_FOLDER
        ) as tf:
            sf.write(tf.name, arr, sample_rate, subtype="PCM_16")
            tmp_wav = tf.name  
        
        transcribed_text, succeed = await asyncio.to_thread(voice.transcribe_voice, tmp_wav)
        
        if succeed and transcribed_text:
            await ws.send_text(f"TRANSCRIPT::{transcribed_text}")
            await ws.send_text(f"AI_RESPONSE::{transcribed_text}")
            
            # ------------------------- # 
            # 3️⃣ Generate TTS with Piper ONNX 
            # # ------------------------- 
            
            tts_chunks  = await asyncio.to_thread(tts.synthesize, str(transcribed_text)) 
            chunk_list = list(tts_chunks)
            
            # Concatenate all audio chunks using audio_int16_array (already PCM16)
            audio_arrays = [chunk.audio_int16_array for chunk in chunk_list]
            pcm16 = np.concatenate(audio_arrays)
            
            # Send the audio data
            await ws.send_bytes(pcm16.tobytes())

        
    except Exception as e:
        print("⚠️ Error during transcription:", e)
    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)

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
    silence_threshold = 5
    voiced_frames = bytearray()

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
                               
                # start of speech
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
                    # Launch async transcription without blocking main loop
                    asyncio.create_task(process_speech(voiced_frames, sample_rate, ws))                    
                    
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
