from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from utils.authentication import AuthUser, get_current_user
from repository.voicecpp import VoiceRepositoryCpp
router = APIRouter(prefix="/stream", tags=["stream"])

@router.websocket("/text")
async def textin(ws: WebSocket):    
    await ws.accept()

    try:
        while True:
            data = await ws.receive_text()
            print(f"User sent: {data}")
            await ws.send_text(f"User: {data}")
    except WebSocketDisconnect:
        print(f"User disconnected")

@router.websocket("/voicein")
async def voicein(ws: WebSocket):
    await ws.accept()
    audio_buffer = b""

    try:
        while True:
            msg = await ws.receive()

            if "bytes" in msg:
                audio_buffer += msg["bytes"]

            elif "text" in msg and msg["text"] == "__STOP__":
                print("Stop signal received")
                break

        # Now process accumulated audio
        voice = VoiceRepositoryCpp()
        transcribed_text, unique_name = await voice.transcribe_voice(audio_buffer, "testuser")
        print(unique_name, transcribed_text)

        await ws.send_text(f"Final transcript: {transcribed_text}")

    except WebSocketDisconnect:
        print("Voice WebSocket disconnected")