from llm.states import SharedState
from langchain_core.messages import BaseMessage

async def save_short_message(state: SharedState):
    """
    Save a short-term message into the shared state memory.

    Args:
        state (SharedState): The current conversation state.
        role (str): "user" or "assistant"
        content (str): The message text.

    Returns:
        dict: Updated state with STM message appended.
    """
    # Optionally enforce STM limit (e.g., keep last 5 messages only)
    STM_LIMIT = 5

    # Ensure messages list exists
    # Append the new message
    messages = [{"role": "user", "content": state.get("input_message", "")}]

    # Add the AI messages (convert BaseMessages -> dicts)
    ai_messages = state.get("messages", [])
    for m in ai_messages:
        if isinstance(m, BaseMessage):
            role = "assistant" if m.type == "ai" else "user"
            messages.append({
                "role": role,
                "content": m.content
            })
        else:
            # Already dict-like
            messages.append(m)

    if len(messages) > STM_LIMIT:
        messages = messages[-STM_LIMIT:]

    # # Return updated state
    # return {
    #     **state,
    #     "short_messages": messages
    # }