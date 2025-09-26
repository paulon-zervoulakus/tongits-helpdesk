
from datetime import datetime
from llm_model import base_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks.manager import get_openai_callback

from typing import List 
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph.state import RunnableConfig
from ai_v2.states import AgentState, IntentList



# --- GRAPH NODES ---
def node_classify_intent(state: AgentState) -> AgentState:
    """Classify intent using LLM."""    
    intent_parser = PydanticOutputParser(pydantic_object=IntentList)

    format_instructions = intent_parser.get_format_instructions()
    # Escape { and } so they are treated literally
    escaped_format_instructions = format_instructions.replace("{", "{{").replace("}", "}}")

    system_prompt = f"""
You are an intent classifier for a Tongits assistant.
Classify the user's input into one or more of these categories and provide the phrase that indicates the intent:
- availability : Phrases from the users message that indicates their availability or interest for the event.
- game_rules : Phrases from the users message that indicates a question about Tongits rules or gameplay.
- registration : Phrases that indicates the user is joining the event.
- neutral : Anything else that is not listed above.
    
IMPORTANT RULES:
- Use phrase that is relative to the original user's message
- DO NOT invent phrase just to satisfy the intent

You MUST return ONLY valid JSON that matches this schema:
{escaped_format_instructions}

No explanations. No extra text. Only JSON.
"""

    intent_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{user_message}")
    ])   

    chain = intent_prompt | base_llm | intent_parser

    with get_openai_callback() as cb:
        start_time = datetime.now()
        response = chain.invoke({
            "user_message": state.get("input_message", "")
        })

        print("**********************************")        
        print("--- node_classify_intent ---")
        print(f"Prompt tokens: {cb.prompt_tokens}")
        print(f"Completion tokens: {cb.completion_tokens}")
        print(f"Total tokens: {cb.total_tokens}")
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nTime spent: {elapsed:.3f}")
        # print(json.dumps(llm_output, indent=4, ensure_ascii=False, default=str))
        # print("----- Current State -----")
        # print(json.dumps(state, indent=4, ensure_ascii=False, default=str))        
        print(f"[DEBUG] classify_intent response: {response.dict()}")
        print("**********************************")
        

        return {
            **state,
            "intent": [item.intent for item in response.intent_list],
            "intent_list": response
        }