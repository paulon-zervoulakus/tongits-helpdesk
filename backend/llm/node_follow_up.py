from llm.states import SharedState

async def follow_up(state: SharedState):
    """Node follow_up."""
    print(f"\n============================= follow_up")

    print(state["input_message"])
    return {
        **state,
        "short_message": "node follow up"
    }