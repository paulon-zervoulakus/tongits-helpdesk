# routes/stream.py
import webrtcvad, asyncio
import numpy as np, soundfile as sf, tempfile, os, traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from repository.voicecpp import VoiceRepositoryCpp
from collections import deque
from schema.sound import UPLOAD_TEMP_FOLDER, VOICE_MODEL_PATH, VOICE_CONFIG_PATH
from piper.voice import PiperVoice
from ai_v2.node_main import build_graph as BuildGraph
from utils.ws_auth import validate_access_token
from ai_v2.states import AgentState
from langgraph.graph.state import RunnableConfig
from typing import Dict, Optional
from utils.cleaner import clean_transcript  
router = APIRouter(prefix="/stream", tags=["stream"])
voice = VoiceRepositoryCpp()
tts = PiperVoice.load(VOICE_MODEL_PATH, VOICE_CONFIG_PATH)
graph = BuildGraph()

# Track active tasks per user
active_tasks: Dict[str, asyncio.Task] = {}

async def process_speech(voiced_frames: bytes, sample_rate: int, ws: WebSocket, user: dict, current_message_parts: list):
    """Handle one full utterance (PCM16) from frontend"""
    user_id = user["sub"]
    tmp_wav = None
    try:
        arr = np.frombuffer(voiced_frames, dtype=np.int16)  # PCM16 little-endian
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=UPLOAD_TEMP_FOLDER) as tf:
            tmp_wav = tf.name
            sf.write(tf.name, arr, sample_rate, subtype="PCM_16")

        await ws.send_text("BEFORE TRANSCRIPTION")
        transcribed_text, succeed = await asyncio.to_thread(voice.transcribe_voice, tmp_wav)
        
        # Ensure it's a string
        if not isinstance(transcribed_text, str):
            print(f"Invalid transcription result type: {type(transcribed_text)}")
            return
        
        transcribed_text = clean_transcript(transcribed_text)
        if succeed and transcribed_text:
            await ws.send_text(f"TRANSCRIPT::{transcribed_text}")
            if user_id in active_tasks and not active_tasks[user_id].done():
                await ws.send_text("CANCEL_AUDIO")
                active_tasks[user_id].cancel()

            # Add new transcribed text to current message parts
            current_message_parts.append(transcribed_text)
            
            # Combine all message parts into one message
            combined_message = " ".join(current_message_parts)
            
            if combined_message == "":
                return
            # -------------------------
            # AI Implementation - Restart with combined message
            # -------------------------
            init_state: AgentState = {
                "input_message": combined_message,
                "fullname": user["name"],
                "email": user["email"],
                "raw_messages": []              
            }
            config: RunnableConfig = {
                "configurable": {
                    "thread_id": user_id,
                    "checkpoint_ns": "chat"
                }    
            }
                        
            try:
                # Create new graph task
                # graph_task = asyncio.create_task(graph.ainvoke(init_state, config=config))
                # active_tasks[user_id] = graph_task
                
                # # Wait for graph completion
                # reply = await graph_task
                
                # Only clear message parts if we got a successful complete response
                reply = {
                    "messages": [
                        {
                            "role": "system",
                            "content": combined_message
                        }
                    ],
                    "graph": {
                        "type": "none",
                        "data": [],
                        "note": "Placeholder graph response"
                    }
                }
                graph_task = None
                current_message_parts.clear()
                print(f"✅ Graph completed successfully, cleared message parts")
                await ws.send_text("GRAPH_COMPLETE") # Delete soon
            except asyncio.CancelledError:
                print(f"🛑 Graph task was cancelled for user {user_id}")
                # Keep current_message_parts so they can be used in next invocation
                return
            except Exception as graph_error:
                print(f"❌ Graph error: {graph_error}")
                traceback.print_exc()
                return
            finally:
                # Clean up the task reference                
                if user_id in active_tasks and active_tasks[user_id] == graph_task:
                    del active_tasks[user_id]
            
            if reply.get("messages") and len(reply["messages"]) > 0:
                # ------------------------- 
                # 3️⃣ Generate TTS with Piper ONNX 
                # -------------------------             
                messages = reply.get("messages", [])
                if messages:
                    last_ai_message = messages[-1]
                    
                    message_text = last_ai_message.content if hasattr(last_ai_message, 'content') else str(last_ai_message)
                    
                    if message_text:
                        await ws.send_text(f"AI_RESPONSE::{message_text}")
                        
                        print("🎤 Starting TTS synthesis task")
                        # Create cancellable TTS task
                        await ws.send_text("BEFORE SYNTHESIZING") # Delete soon
                        tts_task = asyncio.create_task(
                            asyncio.to_thread(tts.synthesize, str(message_text))
                        )
                        await ws.send_text("AFTER SYNTHESIZING") # Delete soon
                        print("🎤 After TTS synthesis task")
                        try:
                            tts_chunks = await tts_task
                            chunk_list = list(tts_chunks)

                            # Concatenate all audio chunks using audio_int16_array (already PCM16)
                            audio_arrays = [chunk.audio_int16_array for chunk in chunk_list]
                            pcm16 = np.concatenate(audio_arrays)
                            # Send the audio data
                            await ws.send_text("BEFORE SENDING BYTES") # Delete soon
                            await ws.send_bytes(pcm16.tobytes())
                            await ws.send_text("AFTER SENDING BYTES") # Delete soon
                            
                        except asyncio.CancelledError:
                            print(f"TTS task cancelled for user {user_id}")
                            return
    except Exception as e:
        print("⚠️ Error during transcription:", e)
    finally:
        if 'tmp_wav' in locals() and os.path.exists(tmp_wav):
            os.remove(tmp_wav)

@router.websocket("/voicein")
async def voicein(ws: WebSocket):
    print("New WebSocket connection attempt")
    await ws.accept()

    token = ws.query_params.get("token")
    is_valid_token, result_validation = await validate_access_token(token)
    if not is_valid_token:
        print(f"❌ Invalid token, closing connection: {result_validation}")
        await ws.close(code=result_validation)
        return
    
    print("Voice WebSocket connected ✅")

    user = result_validation.to_dict()
    user_id = user["sub"]


    # VAD setup
    vad = webrtcvad.Vad(1)  # 0=least aggressive, 3=most aggressive    
    sample_rate = 16000
    frame_ms = 30  # 10, 20, or 30 ms only allowed
    frame_bytes = int(sample_rate * frame_ms / 1000) * 2  # int16=2 bytes

    ring_buffer = deque(maxlen=10)  # short-term buffer to detect speech end
    speech_buffer = bytearray()
    in_speech = False
    silence_threshold = 1
    voiced_frames = bytearray()
    
    # Track current message parts for this user session (replaces accumulated_messages)
    current_message_parts = []

    try:
        while True:
            pcm_bytes = await ws.receive_bytes()   # receive full utterance
            
            # directly launch transcription for this utterance
            asyncio.create_task(
                process_speech(pcm_bytes, 16000, ws, user, current_message_parts)
            )
            # msg = await ws.receive_bytes()  # PCM16 (16kHz, mono)
            # speech_buffer.extend(msg)

            # # process in fixed-size frames for VAD
            # while len(speech_buffer) >= frame_bytes:
            #     frame = speech_buffer[:frame_bytes]
            #     speech_buffer = speech_buffer[frame_bytes:]

            #     is_speech = vad.is_speech(frame, sample_rate) # detect if the frame has speech or silence
            #     ring_buffer.append((frame, is_speech)) # append a tuple [(F1,true), (F2,false), (F3,true), (F4, true), (F5,false), (F6, true), (F7, false), (F8, true), (F9, false),..]
                               

            #     # start of speech
            #     if is_speech and not in_speech:
            #         in_speech = True
            #         voiced_frames = bytearray()
            #         for f, _ in ring_buffer:
            #             voiced_frames.extend(f)
            #         # Do NOT clear ring_buffer here; let it accumulate for silence detection

            #     if in_speech:
            #         voiced_frames.extend(frame)
                
            #     # if silence detected for long enough → end of speech
            #     if in_speech and sum(1 for _, s in ring_buffer if not s) > silence_threshold:                    
            #         # Launch async transcription without blocking main loop
            #         print("🛫 Detected end of speech, launching transcription task")
            #         task = asyncio.create_task(
            #             process_speech(voiced_frames, sample_rate, ws, user, current_message_parts)
            #         )
                    
            #         in_speech = False
            #         ring_buffer.clear()  # Only clear here, after silence detected
            #         voiced_frames = bytearray()
            #     else:
            #         msg = f"...continuing speech: in_speech={in_speech}, ring_buffer_silences={sum(1 for _, s in ring_buffer if not s)}"
            #         print(msg.ljust(80), end='\r', flush=True)
                    
    except WebSocketDisconnect:
        print("❌ Client disconnected")
        # Cancel any active tasks for this user
        if user_id in active_tasks:
            active_tasks[user_id].cancel()
            del active_tasks[user_id]
    except Exception as e:
        print("⚠️ Server error:", e)
        traceback.print_exc()
    finally:
        print("🔒 WebSocket closed")
        # Clean up any remaining tasks
        if user_id in active_tasks:
            active_tasks[user_id].cancel()
            del active_tasks[user_id]