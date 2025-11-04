import json
from datetime import datetime
from langchain_core.messages import AIMessage
from ai_v2.states import AgentState
from langchain_core.prompts import ChatPromptTemplate
from llm_model import base_llm
from langchain_community.callbacks.manager import get_openai_callback
from langgraph.graph.state import RunnableConfig

def node_consolidator_manager(state: AgentState, config: RunnableConfig) -> AgentState:
    """This node is a consolidator of all raw message coming from the AI and the tools results."""
    
    PERSUASION_PROMPT = """
Your task is to consolidate and respond naturally based on the user's question, relevant information from raw_messages, and the conversation summary.

CONSOLIDATION PRIORITY:
1. Action requests take priority — if raw_messages include requests for information (such as registration details, nicknames, confirmations), address those prominently.
2. Maintain conversational flow by seamlessly integrating pending requests with factual information.
3. Avoid redundancy — do not repeat information multiple times.
4. Your answer is what will the user see. So you need to answer as if you were talking directly to the user.
5. Do NOT output any notes or reasoning steps. Only output the natural user-facing message.

INSTRUCTIONS:
1. Scan raw_messages for any pending actions requiring user input, such as registration details or confirmations.
2. Use raw_messages as your primary source of factual information when answering the user's question.
3. Reference the conversation summary for additional context or background.
4. If raw_messages contain relevant event details, use them to provide a helpful, natural response.
5. If no relevant information is available, provide encouragement and persuasion to join upcoming (future) events.
6. Always respond conversationally and naturally — avoid repeating labelled or raw information.
7. Use actual data from raw_messages; do not insert placeholders or fictional data.
8. Mention actual names, event titles, dates, and locations from raw_messages.
9. Include all relevant details: organizer names, event descriptions, location, dates, and times.
10. Prioritize addressing any outstanding user requests found in raw_messages.

⚠️ CRITICAL RULE — DATE VALIDATION (DO NOT IGNORE):
- Before suggesting or inviting the user to join an event, you MUST compare the event date against the current date.
- If the event date is **before** the current date, that event is already over.
  - Do **not** invite the user.
  - Instead, respond naturally that the event has already taken place, and summarize what happened if information is available.
- If the event date is **after or equal** to the current date, the event is upcoming — you may invite or encourage participation.

You MUST follow this date rule strictly — even if the user expresses interest or asks about joining.

EXAMPLES:
Current Date: 2025-10-04  
Event Date: 2025-09-30  
→ Response: "That event already took place last September 30. It was organized by Roshan at the River Bottom arena. There might be similar events coming up though — would you like me to check?"

Current Date: 2025-10-04  
Event Date: 2025-10-10  
→ Response: "There's an upcoming event on October 10! It's organized by Roshan at the River Bottom. I can help you register if you're interested."

---

Current Date: {current_date_time}

User question: {user_message}

Available information (use actual data, not examples): {raw_messages}

Summary of conversation: {conversation_summary}

Now, provide a natural, helpful response using the actual data from raw_messages while following all instructions and date rules strictly.
"""


#     print(f"[DEBUG] - node_consolidator_manager state: ")
#     print(json.dumps(state, indent=4, ensure_ascii=False, default=str))
    try:        
        raw_messages = ", ".join([item for item in state.get("raw_messages", [])])

        # print(f"[DEBUG] - node_consolidator_manager raw_messages: {raw_messages}")
        # Create persuasion tools 
        user_message = state.get("input_message", "")
        # Create Elena agent
        persuasion_prompt = ChatPromptTemplate.from_template(PERSUASION_PROMPT)                  
        
        chain = persuasion_prompt | base_llm
        
        with get_openai_callback() as cb:

            start_time = datetime.now()
            try:
                llm_output = chain.invoke({
                    "raw_messages": raw_messages,
                    "user_message": user_message,
                    "conversation_summary": state.get("short_message",""),
                    "current_date_time": datetime.now().isoformat()
                }, config=config)      
            except Exception as e:
                # LangGraph provides more specific exception types
                print(e)
                llm_output = AIMessage(content="I need a more specific question to help you.")
               
            # Execute persuasion agent
            print("**********************************")
            print("--- node_consolidator_manager ---")
            print(f"Prompt tokens: {cb.prompt_tokens}")
            print(f"Completion tokens: {cb.completion_tokens}")
            print(f"Total tokens: {cb.total_tokens}")
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\nTime spent node_consolidator_manager: {elapsed:.3f}")            
            print("**********************************")
            return {
                **state,
                "messages":llm_output
            }
        
    except Exception as e:
        print(f"Error in node_consolidator_manager: {e}")       
        return {
            **state,
            "messages": AIMessage(content="Sorry, I'm having trouble consolidating the messages right now. Please try again later.")    
        }