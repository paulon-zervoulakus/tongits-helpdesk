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
    
    PERSUASION_PROMPT = """Your task is to respond naturally based on the user's question and relevant information from the raw_messages (your primary facts) and conversation summary (for context).

INSTRUCTIONS:
1. Use the raw_messages as your primary source of facts to answer the user's question
2. Reference the conversation summary for additional context about what has been discussed previously
3. If the information contains relevant details to answer the user's question, use that information to provide a helpful, natural response
4. If there's no relevant information available, then provide encouragement and persuasion to join events
5. Always respond naturally and conversationally - don't repeat the raw information or use labels like "RESPONSE:"
6. Be factual based on the raw_messages, and do not use placeholders
7. Mention the actual names from the raw_messages, not placeholders
8. Include ALL relevant details from the raw_messages - don't leave out important information like organizer names, full event descriptions, location, time and date, or specific details
9. Use the conversation summary to avoid repeating information already discussed and to maintain context

EXAMPLES:

User: "When is the next event?"
Available information: "Community Game Night on Tuesday, September 30 at 07:00 PM"
Conversation summary: "User previously asked about game types available"
Good response: "The next event is the Community Game Night happening on Tuesday, September 30 at 7:00 PM."

User: "What events do you have?"  
Available information: "Community Game Night on Tuesday, September 30 at 07:00 PM - A fun night of Tongits and other card games. (Organized by Paulon Zervoulakus)"
Conversation summary: "New conversation, no previous context"
Good response: "We have a Community Game Night scheduled for Tuesday, September 30 at 7:00 PM. It's a fun night of Tongits and other card games, organized by Paulon Zervoulakus."

User: "I'm thinking about joining"
Available information: [empty]
Conversation summary: "User has been asking about events and showed interest"
Good response: "That's wonderful! Based on our conversation, I can see you're interested in our events. Our Tongits events are a great way to meet fellow players, improve your skills, and have a fantastic time. Many players have joined and really enjoyed the experience!"

---

User question: {user_message}

Available information: {raw_messages}

Summary of conversation: {conversation_summary}

Provide a natural, helpful response:"""

#     print(f"[DEBUG] - node_consolidator_manager state: ")
#     print(json.dumps(state, indent=4, ensure_ascii=False, default=str))
    try:        
        raw_messages = ",".join([
            item.content if isinstance(item.content, str) else str(item.content)
            for item in state.get("raw_messages", [])
            if hasattr(item, 'content')
        ])

        # print(f"[DEBUG] - node_consolidator_manager raw_messages: {raw_messages}")
        # Create persuasion tools 
        user_message = state.get("input_message", "")
        # Create Elena agent
        persuasion_prompt = ChatPromptTemplate.from_template(PERSUASION_PROMPT)                  
        
        chain = persuasion_prompt | base_llm
        
        with get_openai_callback() as cb:
            start_time = datetime.now()
            # Execute persuasion agent
            print("**********************************")
            print("--- node_consolidator_manager ---")

            try:
                llm_output = chain.invoke({
                    "raw_messages": raw_messages,
                    "user_message": user_message,
                    "conversation_summary": state.get("short_message","")
                }, config=config)      
            except Exception as e:
                # LangGraph provides more specific exception types
                print(e)
                llm_output = AIMessage(content="I need a more specific question to help you.")
               
            print(f"Prompt tokens: {cb.prompt_tokens}")
            print(f"Completion tokens: {cb.completion_tokens}")
            print(f"Total tokens: {cb.total_tokens}")
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\nTime spent: {elapsed:.3f}")            
            print("**********************************")
            return {
                **state,
                "messages":llm_output
            }
        
    except Exception as e:
        print(f"Error in node_persuasion: {e}")       
        return {
            **state,
            "messages": AIMessage(content="Sorry, I'm having trouble consolidating the messages right now. Please try again later.")    
        }