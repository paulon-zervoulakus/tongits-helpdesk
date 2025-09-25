from collection_db import chroma_client, embedder, GAME_COLLECTION_NAME
from langchain_core.tools import tool
from ai_v2.states import AgentState

# --- TOOLS here ---
@tool
def update_userform(state: AgentState, nickname: str = "", availability: str = "") -> str:
    """
    Update user form with nickname and/or availability information.
    
    Args:
        state: Current agent state
        nickname: User's preferred nickname or name (optional)
        availability: User's availability information like time, date, day (optional)
    
    Returns:
        Confirmation message of what was updated
    """
    updates = []
    
    if nickname and nickname.strip():
        state["nickname"] = nickname.strip()
        updates.append(f"nickname set to '{nickname}'")
    
    if availability and availability.strip():
        state["availability"] = availability.strip()
        updates.append(f"availability set to '{availability}'")
    
    if updates:
        return f"Successfully updated: {', '.join(updates)}"
    else:
        return "No valid updates provided"

