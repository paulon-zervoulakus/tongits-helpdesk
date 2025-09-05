"""This is the Intent Classifier graph"""
from datetime import datetime
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage
from llm_model import base_llm
from llm.states import SharedState
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

# # @tool
# def tool_last_ai_message(state: SharedState) -> str:
#     """Return the last AI message in the state"""
#     if state.get("messages") and len(state.get("messages")) > 0:
#         ai_messages = [msg for msg in state.get("messages") if isinstance(msg, AIMessage)]
#         if ai_messages:
#             return ai_messages[-1].content
#         else:
#             return ""
#     else:
#         return ""


def prompt_modifier():
    """Prompt modifier is used for SystemMessage."""
    return """
You are an intent classifier for a Tongits help desk. 
Your task is to analyze the user’s latest message and decide if it is:

- "general_question": The user is asking a new question about Tongits (rules, scoring, instructions, gameplay, etc.), independent of previous context.
- "fallback": The user’s request does not match the game or ongoing context.

Instructions:
1. Only return the string with the detected intent/s.
2. Do not add explanations or extra text.

Examples:

Previous conversation: "Hi"
User: "How do you win in Tongits?"
Output: "general_question"

Previous conversation: "How many cards are dealt in Tongits?"
User: "What is the capital of France?"
Output: "fallback"

Previous conversation: "Is it allowed to raise draw?"
User: "I raise to draw, im Pau"
Output: "general_question, fallback"
"""

# # Create the LCEL chain
# prompt = PromptTemplate(
#     input_variables=["message","tool_last_ai_message"],
#     template=prompt_modifier() + "\n\nInput: {message}\n→"
# )

# Modern LCEL approach
# intent_chain = prompt | base_llm | tool_last_ai_message | StrOutputParser()


async def intent_classifier(state: SharedState) -> SharedState:
    """Node intent classifier."""
    print(f"\n============================= intent_classifier")

    print(f"\nTime check\n - before llm: intent_classifier")
    start_time = datetime.now()

    # ai_last_response = tool_last_ai_message(state)

    prompt = PromptTemplate(
        input_variables=["message"],
        template=prompt_modifier() + "\n\nInput: {message}\n→"
    )

    intent_chain = prompt | base_llm | StrOutputParser()

    llm_result = await intent_chain.ainvoke({
        "message": state["input_message"]
    })
    # llm_result = ""
    # chunk_count = 0
    # async for chunk in intent_chain.astream({"message": state["input_message"]}, config, stream_mode="update"):
    #     # for node_name, node_result in chunk.items():
    #     llm_result += chunk
    #     chunk_count += 1

    result_content = [item.strip() for item in llm_result.split(",")]

    # Validation and fallback
    try:
        updated_intent_result=[]
        for intent in result_content:
            if intent not in ["general_question", "fallback"]:
               updated_intent_result.append("fallback")
            else:
                updated_intent_result.append(intent)
        # Remove duplicates by converting to a set and back to a list
        updated_intent_result = list(set(updated_intent_result))

        # Define the priority order (highest priority first)
        priority_order = ["general_question", "fallback"]

        # Sort the list according to the priority
        updated_intent_result.sort(
            key=lambda x: priority_order.index(x) if x in priority_order else len(priority_order))

        result_content = updated_intent_result

        if not isinstance(result_content, list) or not result_content:
            result_content = ["fallback"]
    except Exception as e:
        print(f"Error processing intent: {e}")
        result_content = ["fallback"]

    print(f"\nIntent List: {result_content}")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after llm: intent_classifier - time: {elapsed:.3f}")

    return {
        **state,
        "intent": result_content
    }