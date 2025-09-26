from ai_v2.states import AgentState
from langchain_core.runnables import RunnableConfig
from llm_model import base_llm

MESSAGE_COUNT = 5

def node_msg_summarizer(state: AgentState, config: RunnableConfig) -> AgentState:
    messages = state.get("messages", [])
    
    # Get the last MESSAGE_COUNT messages
    last_messages = messages[-MESSAGE_COUNT:] if len(messages) >= MESSAGE_COUNT else messages
    
    # If no messages to summarize, return state unchanged
    if not last_messages:
        return state
    
    # Format messages for summarization
    messages_text = ""
    for i, msg in enumerate(last_messages, 1):
        content = msg.content
        
        # Detect message type for better role identification
        msg_type = type(msg).__name__
        if msg_type == 'HumanMessage':
            role = 'Human'
        elif msg_type == 'AIMessage':
            role = 'AI'
        elif msg_type == 'SystemMessage':
            role = 'System'
        elif msg_type == 'FunctionMessage' or msg_type == 'ToolMessage':
            role = 'Tool'
        else:
            # Fallback to the role attribute if available
            role = getattr(msg, 'role', msg_type)
        
        messages_text += f"{i}. [{role}]: {content}\n"
    
    # Create summarization prompt
    summary_prompt = f"""Please provide a concise summary of the following conversation messages. 
Focus on key points, decisions, and important context:
    
{messages_text}

Provide a brief summary that captures the essential information and flow of the conversation.
"""
    
    try:
        # Use the base LLM to create summary
        summary_response = base_llm.invoke(summary_prompt, config)
        short_message = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
        
        # Update state with the summary
        updated_state = state.copy()
        updated_state["short_message"] = short_message
        
        return updated_state
        
    except Exception as e:
        # If summarization fails, return original state
        print(f"Message summarization failed: {e}")
        return state