""" Chat routes """
from enum import unique
from fastapi import APIRouter, Depends, UploadFile
from langgraph.graph.state import RunnableConfig
from utils.authentication import AuthUser, get_current_user
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Literal
from repository.voice import VoiceRepository
from llm.node_main import build_graph
from llm.states import SharedState

router = APIRouter(prefix="/api", tags=["chat"])
graph = build_graph()

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile,
    current_user: AuthUser = Depends(get_current_user)
):    
    voice = VoiceRepository()

    transcribed_text, unique_name = await voice.save_voice(file, current_user.sub)
    
    message_text = ""
    if transcribed_text != "":    
        init_state: SharedState = {
            "input_message": transcribed_text,
            "messages": []
        }
        config: RunnableConfig = {
            "configurable": {
                "thread_id": current_user.sub,
                "checkpoint_ns": "chat"
            }    
        }
        reply = await graph.ainvoke(init_state, config=config)    
        
        if reply.get("messages") and len(reply["messages"]) > 0:
            # Collect all AI messages
            ai_messages = [msg for msg in reply["messages"] if hasattr(msg, 'type') and msg.type == 'ai']

            if ai_messages:
                # Get only the last AI message's content
                last_ai_message = ai_messages[-1]
                message_text = last_ai_message.content if hasattr(last_ai_message, 'content') else str(last_ai_message)
            else:
                # No AI messages found
                message_text = reply.get("short_message", "No AI response generated")
                if isinstance(message_text, list):
                    message_text = message_text[-1] if message_text else "No AI response generated"
        else:
            # Fallback if no messages
            message_text = reply.get("short_message", "No response generated")
            if isinstance(message_text, list):
                message_text = message_text[-1] if message_text else "No response generated"

    # Return response with both transcription & file URL
    return JSONResponse({
        "text": transcribed_text,
        "ai_response": message_text,
        "audioUrl": f"/audio/{unique_name}",
        "tag": "transcribed"  # so frontend knows this is voice-origin
    })

# -------------------------
# Schemas
# -------------------------
class ChatIn(BaseModel):
    text: str

class MessageOut(BaseModel):
    ai_response: str
    source: Literal["text", "voice", "bot"]

@router.post("/chat", response_model=MessageOut)
async def chat_text(
    in_: ChatIn,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Simple chat endpoint. Replace the bot logic with your own later.
    """
    user_text = in_.text.strip()
    # demo “bot” logic – echo with a little formatting
    init_state: SharedState = {
        "input_message": user_text,
        "messages": []
    }
    config: RunnableConfig = {
         "configurable": {
            "thread_id": current_user.sub,
            "checkpoint_ns": "chat"
        }    
    }
    reply = await graph.ainvoke(init_state, config=config)    
    
    if reply.get("messages") and len(reply["messages"]) > 0:
        # Collect all AI messages
        ai_messages = [msg for msg in reply["messages"] if hasattr(msg, 'type') and msg.type == 'ai']

        if ai_messages:
            # Get only the last AI message's content
            last_ai_message = ai_messages[-1]
            message_text = last_ai_message.content if hasattr(last_ai_message, 'content') else str(last_ai_message)
        else:
            # No AI messages found
            message_text = reply.get("short_message", "No AI response generated")
            if isinstance(message_text, list):
                message_text = message_text[-1] if message_text else "No AI response generated"
    else:
        # Fallback if no messages
        message_text = reply.get("short_message", "No response generated")
        if isinstance(message_text, list):
            message_text = message_text[-1] if message_text else "No response generated"


    
    return MessageOut(ai_response=message_text, source="bot")