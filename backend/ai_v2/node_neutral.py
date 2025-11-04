# def agent(state: AgentState, config: RunnableConfig) -> AgentState:
#     """Build stage-aware response using LLM."""
#     stage = state.get("stage", 1)
#     user_msg = state["input_message"]
#     intent = state.get("intent", "neutral")
#     ack_options = ACKS.get(intent, ACKS["neutral"])
#     acknowledgement = f"""
# You always acknowledge the user’s input from one of the list below if necessary.
# Options: {", ".join(ack_options)}
# """
#     # Build prompt template for ReAct agent
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", SYSTEM_PROMPT),
#         ("system", "Stage instructions:\n{stage_instructions}"),
#         ("system", FORM),
#         ("system", "{acknowledgement}"),
#         ("human", "Users message:\n{user_message}"),
#         ("assistant","{agent_scratchpad}"),
#         ("system", "{tool_names}"),
#         ("system","{tools}")
#     ])

#     stage_instructions = STAGE_PROMPTS.get(stage, STAGE_PROMPTS[1])
#     tools = [update_userform, game_ruling]
#     tool_names = [tool.name for tool in tools]
#     agent = create_react_agent(llm=base_llm, tools=tools, prompt=prompt)
#     agent_executor = AgentExecutor.from_agent_and_tools(
#         agent=agent,
#         tools=tools,
#         verbose=True,
#         max_iterations=3,
#         handle_parsing_errors=True,
#         early_stopping_method="force",
#         max_tokens=2048
#     )

#     with get_openai_callback() as cb:
#         llm_output = agent_executor.invoke({
#             "stage_instructions": stage_instructions,
#             "user_message": user_msg,
#             "fullname": state.get("fullname",""),
#             "email": state.get("email",""),
#             "nickname": state.get("nickname",""),
#             "availability": state.get("availability",""),
#             "acknowledgement": acknowledgement,
#             "tool_names": tool_names,
#             "tools": tools
#         }, config=config)
#         print("**********************************")
#         print(f"Prompt tokens: {cb.prompt_tokens}")
#         print(f"Completion tokens: {cb.completion_tokens}")
#         print(f"Total tokens: {cb.total_tokens}")
#         print(json.dumps(llm_output, indent=4, ensure_ascii=False, default=str))
#         print("----- Current State -----")
#         print(json.dumps(state, indent=4, ensure_ascii=False, default=str))
#         print("**********************************")

#         ai_msg = AIMessage(content=llm_output["output"])
#         state["messages"].append(ai_msg)
#         return state
from datetime import datetime
from ai_v2.states import AgentState
from langgraph.graph.state import RunnableConfig
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.prompts import ChatPromptTemplate
from llm_model import checkpointer, base_llm

def node_neutral(state: AgentState, config: RunnableConfig) -> AgentState:
   
    intents = state.get("intent", [])
    if "neutral" not in intents:
        # This node doesn't handle this intent, return empty raw_messages
        return state
    
    
    NEUTRAL_PROMPT = """Your role is toresponse for casual or neutral conversations.

CONTEXT AWARENESS:
- Use the conversation summary to understand what has been discussed previously
- Build upon previous conversations naturally without repeating information
- Reference past interactions to create a more personalized experience
- If the summary shows previous resistance or interest, adjust your approach accordingly

### INSTRUCTIONS ###
1. Always stay polite, upbeat, and encouraging.
2. If the user just makes small talk, responds briefly.
3. Stay focus on the topic and use conversation summary as needed.
4. If the user resists, you remain friendly, and funny.
5. Use short, clear, natural sentences. Avoid robotic repetition.

### RESPONSE STYLE ###
- Friendly and conversational.
- Slightly playful if appropriate.

---

User message: {intent_phrases}

Conversation summary: {conversation_summary}

Synthesize response:"""

    intent_phrases = ",".join(
        [item.phrase_message for item in state["intent_list"] if item.intent == "neutral"]
    )
    intent_prompt = ChatPromptTemplate.from_template(NEUTRAL_PROMPT)

    chain = intent_prompt | base_llm 

    with get_openai_callback() as cb:
        start_time = datetime.now()
        response = chain.invoke({
            "intent_phrases": intent_phrases,
            "conversation_summary": state.get("short_message","")
        })

        print("**********************************")        
        print("--- node_neutral ---")
        print(f"Prompt tokens: {cb.prompt_tokens}")
        print(f"Completion tokens: {cb.completion_tokens}")
        print(f"Total tokens: {cb.total_tokens}")
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nTime spent node_neutral: {elapsed:.3f}")    
        print("**********************************")
        return {
            **state,
            "raw_messages":  state["raw_messages"].append(response.content)
        }