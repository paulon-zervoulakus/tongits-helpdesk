from typing import Annotated, List, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class SharedState(TypedDict, total=False):    
    """SharedState Schema"""
    input_message: Annotated[str, lambda prev, new: new if new is not None else prev]
    intent: Annotated[List[str], lambda prev, new: new if new is not None else prev]
    short_message: Annotated[List[str], lambda prev, new: new if new is not None else prev]
    messages: Annotated[List[BaseMessage], add_messages]
    