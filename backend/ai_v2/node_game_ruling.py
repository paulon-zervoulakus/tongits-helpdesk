from datetime import datetime
from langchain_core.messages import AIMessage
from llm_model import base_llm
from langchain_core.prompts import ChatPromptTemplate
from ai_v2.states import AgentState
from langchain_community.callbacks.manager import get_openai_callback
from langchain.agents import AgentExecutor, create_react_agent
from langgraph.graph.state import RunnableConfig
from langchain_core.tools import tool
from collection_db import chroma_client, embedder, GAME_COLLECTION_NAME
from ai_v2.states import AgentState

@tool
def tool_game_rules(query: str, top_k: int = 3) -> str:
    """This tool is all about Game Rules regarding Tongits card game.

    Args:
        query: string
        top_k: integer
    
    Returns:
        String containing the most relevant game rules
    """
    # print(f"\n[DEBUG] game_ruling called with query: {query}")
    try:
        conversation_thread_id = GAME_COLLECTION_NAME
        
        try:
            collection = chroma_client.get_collection(conversation_thread_id)
            
            collection_count = collection.count()
            
            if collection_count == 0:
                return f"No documents found in collection '{conversation_thread_id}'."

            try:
                query_embedding = embedder.encode(query)
                
                query_embedding = query_embedding.tolist()
                
            except Exception as embed_error:
                print(f"[DEBUG] Embedding error: {embed_error}")
                return f"Error generating embedding: {str(embed_error)}"
            
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, collection_count),
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as query_error:
                print(f"[DEBUG] Query error: {query_error}")
                return f"Error querying collection: {str(query_error)}"

            if not results["documents"] or not results["documents"][0]:
                print("[DEBUG] No documents in results")
                return "No relevant document rule found."
            
            
            # Format the results
            relevant_history = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0], 
                results["metadatas"][0], 
                results["distances"][0]
            )):
                relevance_score = 1 - min(distance, 2.0) / 2.0  # Normalize distance to 0-1 scale
                message_type = metadata.get("message_type", "unknown")
                timestamp = metadata.get("timestamp", "unknown")
                
                relevant_history.append(
                    f"[{i+1}] {doc}\n"
                    f"   Relevance: {relevance_score:.2f}"
                )
            
            result_text = f"\n\n".join(relevant_history)            
            return result_text
            
        except Exception as collection_error:
            print(f"[DEBUG] Collection error: {collection_error}")
            return f"No document rule found. Collection '{conversation_thread_id}' does not exist. \nQuery: {query}\nError: {str(collection_error)}"
            
    except Exception as e:
        print(f"[DEBUG] Top-level error in game_ruling: {str(e)}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return f"Error searching document rule: {str(e)}"

def node_game_ruling(state: AgentState, config: RunnableConfig) -> AgentState:
    if "game_rules" not in state.get("intent", []):
        return state  # Skip if not relevant
    
    GAME_RULES_PROMPT = """Your role is to synthesize a response to answer questions based on the result of the tool here {tool_names}.
The relevant question is the {user_message}, analyze the result based on the user's message.

TOOLS:
You have access to the following tool(s): {tool_descriptions}
(When calling tools, always use the exact tool id: {tool_names})

OUTPUT FORMAT (must always follow this order):
Thought: One-line summary of what you will do (short and simple)
Action: {tool_names}
Action Input: the user's question in search form (just the string, no JSON)
Observation: [tool results]
Thought: Summarize the observation in 1–2 sentences.
Final Answer: Give the helpful answer.

IMPORTANT EXECUTION RULE:
After you receive an Observation from the tool, you MUST:
- Write a Thought line summarizing what you saw (1–2 sentences).
- Then write a Final Answer for the human.
- Do NOT call any tool again after the first Observation.

CRITICAL RULES:
1. You MUST call {tool_names} exactly once.
2. After the Observation, do NOT call another tool again (see rule above).
3. If the user asks about another game (Poker, Mahjong, etc.), still call {tool_names} once, then explain in Final Answer that you only support Tongits.
4. If the tool returns truncated or no results, still write Observation, then give your best Thought and Final Answer anyway.
5. Never stop before giving a Final Answer. Every output must include all six parts: Thought → Action → Action Input → Observation → Thought → Final Answer.

EXAMPLE 1 - Tongits question:
Human: What is sapaw in Tongits?

Thought: Search the Tongits rules for "sapaw" and summarize.
Action: {tool_names}
Action Input: sapaw in Tongits
Observation: [tool returns results]
Thought: The tool result shows that sapaw means adding cards to an existing meld.
Final Answer: In Tongits, "sapaw" means adding cards to an existing meld on the table, either your own or an opponent's.

EXAMPLE 2 - Truncated result:
Human: What is the lowest deadwood rule?

Thought: Search the Tongits rules for "lowest deadwood" and summarize.
Action: {tool_names}
Action Input: lowest deadwood in Tongits
Observation: Found 3 relevant document rules: [truncated...]
Thought: The tool mentions winning by having the lowest deadwood when the game ends.
Final Answer: In Tongits, besides winning by Tongit, a player can also win by having the lowest deadwood when the game ends.

EXAMPLE 3 - Non-Tongits question:
Human: How to win in Mahjong?

Thought: Search the Tongits rules for "Mahjong win" to confirm coverage.
Action: {tool_names}
Action Input: how to win in Mahjong
Observation: Tool returned only Tongits-related results, no Mahjong rules.
Thought: The database contains Tongits rules but no information about Mahjong.
Final Answer: I can't provide rules for Mahjong, since I only assist with Tongits. If you'd like, ask me any Tongits rule instead!

Begin!
"""

    intent_phrases = ",".join(
        [item.phrase_message for item in state["intent_list"] if item.intent == "game_rules"]
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", GAME_RULES_PROMPT),
        ("system","{agent_scratchpad}"),
        ("system","{tools}")
    ])
    # format tools properly
    tools = [tool_game_rules]
    tool_descriptions = "\n".join(
        [f"- {t.name}: {t.description}" for t in tools]
    )

    agent = create_react_agent(
        llm=base_llm,
        tools=tools,
        prompt=prompt
    )
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=3,
        handle_parsing_errors=True,
        early_stopping_method="force",
        return_intermediate_steps=True  # Key parameter
    )
    with get_openai_callback() as cb:
        start_time = datetime.now()
        try:
            llm_output = agent_executor.invoke(
                {
                    "user_message": intent_phrases,
                    "tool_descriptions": tool_descriptions,
                    "tools": "\n".join([t.name for t in tools]),
                    "tool_names": ", ".join([t.name for t in tools])
                },
                config=config
            )
            ai_msg = llm_output["output"]

            print("**********************************")
            print("--- node_game_ruling ---")
            print(f"Prompt tokens: {cb.prompt_tokens}")
            print(f"Completion tokens: {cb.completion_tokens}")
            print(f"Total tokens: {cb.total_tokens}")
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\nTime spent node_game_ruling: {elapsed:.3f}")
            print("**********************************")
        except Exception as e:
            # LangGraph provides more specific exception types
            if "recursion limit" in str(e):
                ai_msg = "I need a more specific question to help you."
            else:
                ai_msg = "Sorry, I'm having trouble accessing the rules right now. Please try again later."

        

    return {
        **state,
        "raw_messages": state["raw_messages"].append(ai_msg)
    }
