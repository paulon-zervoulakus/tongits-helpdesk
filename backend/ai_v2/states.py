from typing_extensions import Annotated, TypedDict, List
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel

class IntentItem(BaseModel):
    intent: str       # e.g. "nickname", "availability", "neutral", "noise"
    phrase_message: str    # phrase from user's message that indicates the intent

# class IntentList(BaseModel):
#     intent_list: List[IntentItem]

def replace_or_keep(prev: list, new: list):
    if new is None:
        return prev  # keep old if not updated
    if new == []:
        return []    # allow explicit reset
    return new      # replace with whatever new is
# --- STATE ---
class AgentState(TypedDict):    
    input_message: Annotated[str, lambda prev, new: new if new is not None else prev]
    messages: Annotated[List[BaseMessage], add_messages]
    raw_messages: Annotated[List[str], replace_or_keep]
    short_message: Annotated[str, lambda prev, new: new if new is not None else prev]

    intent: Annotated[List[str], lambda prev, new: new if new is not None else prev]
    intent_list: Annotated[List[IntentItem], lambda prev, new: new if new is not None else prev]

    fullname: Annotated[str, lambda prev, new: new if new is not None else prev]
    email: Annotated[str, lambda prev, new: new if new is not None else prev]
    stage: Annotated[str, lambda prev, new: new if new is not None else prev]
    nickname: Annotated[str, lambda prev, new: new if new is not None else prev]    
    event_details: Annotated[str, lambda prev, new: new if new is not None else prev]    