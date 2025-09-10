import json
from datetime import datetime
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from llm.states import SharedState
from llm_model import base_llm, LLM_MODEL
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from collection_db import chroma_client, embedder, GAME_COLLECTION_NAME
from typing import Optional
from langchain_community.callbacks.manager import get_openai_callback

global_thread_id = "xxx"

@tool
def game_ruling(query: str, top_k: int = 3) -> str:
    """Game Rules here 

    Args:
        query: The search query to find relevant game ruling
        top_k: Number of top relevant results to return (default: 5)
    
    Returns:
        String containing the most relevant game rules
    """
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
                    f"[{i+1}] {message_type.upper()} ({timestamp}): {doc}\n"
                    f"   Relevance: {relevance_score:.2f}"
                )
            
            result_text = f"Found {len(relevant_history)} relevant document rules:\n\n" + "\n\n".join(relevant_history)
            
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
        
@tool
def search_conversation_history(
    query: str, 
    filter_user: Optional[bool] = None, 
    top_k: int = 3
    ) -> str:
    """Search through the conversation history to find the most relevant previous messages.
    
    Args:
        query: The search query to find relevant conversation history
        filter_user:
            - True = search only user messages
            - False = search only AI messages
            - None = search both user and AI
        top_k: Number of top relevant results to return (default: 5)
        offset: How many results to skip (for paging).      
    
    Returns:
        String containing the most relevant conversation history
    """
    try:
        global global_thread_id 
        
        # Get thread_id from global variable
        if not global_thread_id or global_thread_id == "xxx":
            return "No conversation thread ID available."
        
        conversation_thread_id = global_thread_id
        
        try:
            collection = chroma_client.get_collection(conversation_thread_id)
        except Exception as e:
            return f"No conversation history found. Collection '{conversation_thread_id}' does not exist. \nQuery: {query}\nError: {str(e)}"
        
        # Check if collection has any documents
        collection_count = collection.count()
        if collection_count == 0:
            return f"No conversation history available in collection '{conversation_thread_id}'."
        
        # Generate embedding for the search query
        try:
            query_embedding = embedder.encode(query).tolist()
        except Exception as e:
            return f"Error generating embedding for query: {str(e)}"
        
        # Search for most relevant documents
        try:
            where = None
            if filter_user is not None:
                to_filter_user = "user" if filter_user else "ai"
                where = {"message_type": to_filter_user}

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
                where=where,
            )
        except Exception as e:
            return f"Error querying collection: {str(e)}"
        
        if not results["documents"] or not results["documents"][0]:
            return "No relevant conversation history found."
        
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
                f"[{i+1}] {message_type.upper()} ({timestamp}): {doc}\n"
                f"   Relevance: {relevance_score:.2f}"
            )
        
        return f"Found {len(relevant_history)} relevant conversation entries:\n\n" + "\n\n".join(relevant_history)
        
    except Exception as e:
        return f"Error searching conversation history: {str(e)}"

def prompt_modifier_gpt():
    return """
system: |
You are a helpful, friendly customer support assistant for the Filipino card game Tongits.
Follow these SYSTEM-LEVEL RULES exactly.

CORE RULES:
1. All factual Tongits information MUST come from the game_ruling tool.
    - If the tool returns zero relevant entries, say exactly: "I couldn't find that information in the official rules."
2. Use recent context or search conversation history when needed (use search_conversation_history tool).
3. You MUST produce output that matches exactly ONE of the two allowed RESPONSE PATTERNS below. Do NOT mix patterns.
4. If you use tools, your output must include ALL fields in the exact order shown, with "Action Input" formatted as a JSON object on the same line.
5. If you do NOT use tools, output only the Final Answer field (see pattern below).
6. If the search results contain ANY explicit mention of the inquiry topic, DO NOT say "I couldn't find." Instead synthesize the result and answer based on those entries.
7. Only say "I couldn't find..." when there are truly zero relevant entries returned by the tool.
8. Keep the Thought: field concise (one short sentence) — it is a brief plan/intent, not a detailed chain-of-thought.
9. Never add content outside the required fields. Extra commentary breaks the downstream parser.

RESPONSE PATTERNS (choose exactly one):
- If using tools (required exact format):
Thought: [one-sentence plan]
Action: [tool_name]
Action Input: {{"param1": "value", "param2": 123}}
Observation: [System/tool will provide results here]
Final Answer: [Full user-facing answer here — REQUIRED]

- If NOT using tools (required exact format):
Final Answer: [Full user-facing answer here — REQUIRED]

developer: |
PROFILE:
- Full Name: Crystal Maiden
- Nickname: Maiden
- Gender: Female
- Age: 25
- Personality: Friendly, supportive, patient, slightly playful
- Background: Expert in Tongits and Filipino card games, trained to assist players
- Communication Style: Provides detailed explanations with examples; uses short paragraphs and bullet points for clarity
- Role to User: Helpful customer support assistant

STYLE & DEFAULTS:
- Be polite, professional, and user-friendly.
- Provide detailed, accurate explanations with context.
- Use short paragraphs for readability and bullet points for lists/steps.
- Expand on reasoning or background only as needed to help the user understand.
- If no information is available, explain that politely and suggest next steps.

TOOLS:
{tools}
Tool names: {tool_names}

IMPORTANT RULES (developer-level):
- ALWAYS output a "Final Answer:" section exactly as shown above.
- If a tool returns nothing, still output Final Answer and ask the user for details or next steps.
- If a tool call fails or returns ambiguous output, explain the failure concisely and ask for clarification.
- Do NOT mix "I couldn't find" with quoted results; either you found relevant content (synthesize it) OR you clearly state nothing was found.

assistant: |
# Example 1 — Direct answer (no tools)
Final Answer: Hello! I'm Crystal Maiden, your Tongits assistant. I can explain Tongits rules, scoring, and gameplay in detail — how can I help you today?

assistant: |
# Example 2 — Game rules (use game_ruling tool)
Thought: Need official melding rules; will query the rules tool.
Action: game_ruling
Action Input: {{"query": "meld formation rules"}}
Observation: [Official melding rules will appear here]
Final Answer: According to the official rules, players form melds by creating sets (same rank, different suits) or runs (consecutive cards same suit). Melds must contain at least three cards. Place melds face-up on your turn. Correct melding reduces deadwood points and affects endgame scoring.

assistant: |
# Example 3 — Conversation history (search)
Thought: User asked about their earlier statement; search conversation history.
Action: search_conversation_history
Action Input: {{"query": "my name", "filter_user": true, "top_k": 10}}
Observation: [Conversation entries will appear here]
Final Answer: Based on our conversation history, you introduced yourself as "Paulo." How would you like me to use that information in this Tongits discussion?

assistant: |
# Example 4 — Tool returns nothing
Thought: Search returned no relevant entries.
Action: search_conversation_history
Action Input: {{"query": "previous topic", "filter_user": true, "top_k": 10}}
Observation: []
Final Answer: I couldn't find any mention of that topic in our conversation history. Could you please share more details or rephrase the question?

user: |
Question: {input}
{agent_scratchpad}"""

def prompt_modifier():
   return """ROLE:
You are a helpful, friendly customer support assistant for the Filipino card game Tongits.

PROFILE:
- Full Name: Crystal Maiden
- Nick Name: Maiden
- Gender: Female

RULES:
1. All Tongits information must come from the game_ruling tool.
2. You may use recent context or search conversation history if needed.
3. Always keep answers clear, polite, and concise.

TOOLS:
{tools}
TOOL_NAMES:
{tool_names}

RESPONSE PATTERN (STRICT):
- If using tools:
  Thought: [Reasoning about the question]
  Action: [tool name]
  Action Input: {{ "parameter": "value" }}
  Observation: [System will provide results]
  Final Answer: [Complete answer here – REQUIRED]

- If not using tools:
  Final Answer: [Complete answer here – REQUIRED]

IMPORTANT RULES:
- Always output a “Final Answer:” section, even if tools fail.
- If tool returns nothing, still give a Final Answer and ask the user for details.
- If tool call fails or is unclear, explain and ask for clarification.
- If the search results contain ANY explicit mention of the inquiry topic, DO NOT say "I couldn't find." instead synthesize the result of the query
- Only say "I couldn't find..." if there are truly zero relevant entries returned.

STYLE:
- Be polite, professional, and user-friendly.
- Provide detailed explanations with context, not just short answers.
- Use short paragraphs for readability.
- Use bullet points when listing steps, rules, or options.
- Expand on reasoning or background where it helps the user understand.

DEFAULT BEHAVIOR:
If no information is available, politely explain and suggest next steps.

---

Question: {input}  
{agent_scratchpad}
"""

async def general_question(state: SharedState, config: RunnableConfig):
    """Node general question."""
    print(f"\n============================= general_question")
    print(f"\nTime check\n - before llm: general_question")
    start_time = datetime.now()
    
    try:
        global global_thread_id 
        global_thread_id = config.get("configurable", {}).get("thread_id")

        tools = [search_conversation_history, game_ruling]
        tool_names = [tool.name for tool in tools]
        # tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        
        prompt = prompt_modifier_gpt() if LLM_MODEL == "gpt-oss-2k:latest" else prompt_modifier()

        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt + "\n\nShort Messages (STM Buffer): {short_messages}"),
            ("human", "{input}"),
            ("assistant", "{agent_scratchpad}"),
            ("system", "{tool_names}")
        ]) 

        agent = create_react_agent(llm=base_llm, tools=tools, prompt=prompt)

        # # Create agent executor with proper configuration
        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=2,
            handle_parsing_errors=True,
            early_stopping_method="force",
            max_tokens=4096
        )
        
        print("Executing agent...")
        with get_openai_callback() as cb:
            try:
                result = await agent_executor.ainvoke(
                    {
                        "input": state["input_message"],
                        "short_messages": "\n".join([f"{m.type}: {m.content}" for m in state["messages"][-6:]]),
                        "tool_names": tool_names
                    }, 
                    config=config
                )
            except StopIteration as stop_err:
                print(f"StopIteration caught: {stop_err}")
                # Fallback to direct LLM call
                result = await fallback_direct_llm(state["input_message"], config)
            except Exception as agent_err:
                print(f"Agent execution error: {agent_err}")
                # Fallback to direct LLM call
                result = await fallback_direct_llm(state["input_message"], config)

            print("**********************************")
            print(f"Prompt tokens: {cb.prompt_tokens}")
            print(f"Completion tokens: {cb.completion_tokens}")
            print(f"Total tokens: {cb.total_tokens}")
            print(json.dumps(result, indent=4, ensure_ascii=False, default=str))
            print("**********************************")
            
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\nTime check\n - after llm: general_question - time: {elapsed:.3f}")
               
        return {
            **state,
            "messages": [
                HumanMessage(content=state["input_message"]),
                AIMessage(content=result["output"])
            ]
        }
        
    except Exception as e:
        print(f"Error in general_question: {str(e)}")

        return {
            **state,
            "messages": [
                HumanMessage(content=state["input_message"]),
                SystemMessage(content=str(e))
            ]
        }


async def fallback_direct_llm(input_message: str, config: RunnableConfig):
    """Fallback to direct LLM call without agent/tools"""
    try:
        prompt = f"""You are Crystal Maiden (call yourself "Maiden"), a helpful assistant for the Filipino card game Tongits.

User question: {input_message}

Please provide a helpful response about Tongits."""
        
        response = await base_llm.ainvoke(prompt, config=config)
        return {"output": response.content if hasattr(response, 'content') else str(response)}
    except Exception as e:
        return {"output": f"I'm having technical difficulties. Error: {str(e)}"}