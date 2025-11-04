import json
from datetime import datetime
from llm_model import base_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks.manager import get_openai_callback

from typing import List 
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph.state import RunnableConfig
from ai_v2.states import AgentState, IntentItem



# --- GRAPH NODES ---
def node_classify_intent(state: AgentState) -> AgentState:
    """Classify intent using LLM."""    
    # intent_parser = PydanticOutputParser(pydantic_object=List(IntentItem))

    # format_instructions = intent_parser.get_format_instructions()
    # # Escape { and } so they are treated literally
    # escaped_format_instructions = format_instructions.replace("{", "{{").replace("}", "}}")

    system_prompt = """Your role is to classify the user's input into one or more intents and extract the EXACT phrase from their message that indicates each intent.

INTENT CATEGORIES (4 intents only):

- availability : Questions about event schedules, dates, times, locations, what events exist
  (EXCLUDES: Any joining or participation interest)

- game_rules : Questions about Tongits rules, gameplay, or how to play

- registration : 
  * Interest in joining/participating
  * Providing personal information (name, email, contact)
  * Confirmation responses
  * Registration questions/actions

- neutral : Greetings, casual chat, off-topic questions, thanks

CRITICAL INSTRUCTIONS FOR phrase_message:
1. Extract the EXACT phrase or sentence from the user's input that matches the intent
2. Use the user's ORIGINAL wording - do NOT paraphrase or rewrite
3. If the intent spans multiple sentences, capture the relevant portion
4. Keep the user's tone, style, and exact words

EXAMPLES:

Input: "Is there an upcoming event this few days ahead? and by the way you can register me as Osmar."
Output: [
  {{"intent": "availability", "phrase_message": "Is there an upcoming event this few days ahead?"}},
  {{"intent": "registration", "phrase_message": "you can register me as Osmar"}}
]

Input: "Hello! What events do you have? I'd like to join."
Output: [
  {{"intent": "neutral", "phrase_message": "Hello!"}},
  {{"intent": "availability", "phrase_message": "What events do you have?"}},
  {{"intent": "registration", "phrase_message": "I'd like to join"}}
]

No explanations. No extra text. Only JSON.
"""

    intent_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{user_message}")
    ])   

    chain = intent_prompt | base_llm 

    try:
        with get_openai_callback() as cb:
            start_time = datetime.now()
            response = chain.invoke({
                "user_message": state.get("input_message", "")
            })
            
            # Parse JSON content into Python list of dicts
            parsed = json.loads(response.content)

            # Convert dicts into Pydantic objects
            result = [IntentItem(**item) for item in parsed]

            print("**********************************")        
            print("--- node_classify_intent ---")
            print(f"Prompt tokens: {cb.prompt_tokens}")
            print(f"Completion tokens: {cb.completion_tokens}")
            print(f"Total tokens: {cb.total_tokens}")
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\nTime spent node_classify_intent: {elapsed:.3f}")    
            print(f"[DEBUG] classify_intent response: {[r.dict() for r in result]}")
            print("**********************************")

    except Exception as e:
        print("Error in Intent classification :", e)
        result = [
            IntentItem(
                intent="neutral",
                phrase_message="My apologies but I cannot understand what you were trying to say. Can you repeat your statement?"
            )
        ]

    return {
        **state,
        "intent": [item.intent for item in result],
        "intent_list": result
    }