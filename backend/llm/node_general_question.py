import json
from datetime import datetime
from langchain_core.messages import AIMessage
from llm.states import SharedState
from llm_model import base_llm
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
    top_k: int = 3,
    offset: int = 0
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

            # ask for enough results (offset + top_k)
            n_fetch = min(offset + top_k, collection_count)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_fetch,
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

def prompt_modifier():
   return """You are Crystal Maiden, a helpful assistant for the Filipino card game Tongits.

### CORE RULES:
1. **Game Rules**: All Tongits information MUST come from game_ruling tool. If not found: "I couldn't find that information in the official rules."
2. **Memory System**: You have two memory sources:
   - STM Buffer (recent messages shown below)
   - search_conversation_history tool (full conversation database)

### AVAILABLE TOOLS:
{tools}

### MEMORY USAGE STRATEGY:
**STM Buffer**: Shows only the last ~10 messages (recent context)
**Full conversation history**: Available via search_conversation_history tool
**Key point**: If user references something from "before" or "earlier", it's likely NOT in STM Buffer
**Always use search_conversation_history** when user asks about previous conversations

### TOOL USAGE:
**search_conversation_history:**
    - query: what you're searching for (e.g., "name", "Paulo", "user introduction")  
    - filter_user: true (search user messages), false (search AI responses), null (search both)
    - top_k: 3, offset: 0
**game_ruling:**
    - For any Tongits gameplay questions

### DECISION PROCESS:
1. **Check STM Buffer first** for immediate context
2. **If information missing from STM**, use appropriate tool:
   - Missing conversation history → search_conversation_history
   - Need game rules → game_ruling
3. **For simple greetings/chat with sufficient context** → respond directly

### RESPONSE FORMAT:
Thought: [Analyze the request. Check STM Buffer. Decide if tools are needed.]
Action: [MUST be one of {tool_names} if a tool is needed. If no tool is needed, skip Action and Action Input entirely, and go directly to Final Answer.]
Action Input: {{"query": "users input", "filter_user": true, "top_k": 3}}
Observation: [Result from the tool, provided by the system]
Final Answer: [One complete consolidated answer]

---

### EXAMPLES:
**User asks about previous conversation (STM insufficient):**
    Thought: User is asking about something from earlier. STM Buffer does not contain the answer, so I must search the full conversation history.
    Action: search_conversation_history
    Action Input: {{"query": "users input", "filter_user": true, "top_k": 3}}

**User asks about Tongits rules:**
    Thought: This is a game rules question. I need the game_ruling tool to provide the correct rule.
    Action: game_ruling
    Action Input: {{"query": "users input"}}

**User asks about previous conversation, STM has sufficient context:**
    Thought: The STM Buffer already contains the correct answer, so I can respond directly without using tools.
    Final Answer: [Provide the answer directly from STM context.]

**User insists on checking conversation history, even if STM has sufficient context:**
    Thought: The user explicitly asked me to check deeper or look into previous chat. Even though STM Buffer has the information, I must still search the conversation history.
    Action: search_conversation_history
    Action Input: {{"query": "users input", "filter_user": true, "top_k": 3}}

---

### CRITICAL RULES:
- STM Buffer might not contain all conversation history  
- When in doubt about previous conversation details, use `search_conversation_history`  
- Always use tools when the user explicitly asks you to "check previous chat" or recall earlier information  
- **After any Observation:**
  - If all user questions are answered → go to Final Answer  
  - If more actions are required → continue with another Thought + Action  
- **Final Answer must always come last, and only once**  

---

### CONSOLIDATION RULE:
- If the user asks multiple questions in one input, you may need to call multiple tools or check STM + history.  
- After all Observations are completed, you MUST produce **one single Final Answer**.  
- The Final Answer must **consolidate all answers** into one coherent, enticing, and complete response.  
- The Final Answer must always be **clear, detailed, and explanatory**, not just short or minimal.  
- When appropriate, provide **examples, step-by-step reasoning, or analogies** to make the answer easier to understand.  
- If the user explicitly asks for “explain further,” “go deeper,” or “expand,” you MUST elaborate more than usual.  
- For game-related details, you MUST use only the `game_ruling` tool’s output. Do not invent rules.  
- For user-related context, rely on STM first, then `search_conversation_history` if needed.  
- If a question cannot be answered from Observations, respond with exactly:  
  `"I couldn't find that information in the official rules."`

---

### FINAL ANSWER FORMAT:
After the last Observation:

   
Begin!

Question: {input}
Thought: {agent_scratchpad}"""

async def general_question(state: SharedState, config: RunnableConfig):
    """Node general question."""
    print(f"\n============================= general_question")
    print(f"\nTime check\n - before llm: general_question")
    start_time = datetime.now()
    
    try:
        global global_thread_id 
        global_thread_id = config.get("configurable", {}).get("thread_id")

        # Create agent with tools using custom prompt (required)
        tools =[search_conversation_history, game_ruling]
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_modifier() + "\n\nShort Messages (STM Buffer): {short_messages}"),
            ("human", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])        

        agent = create_react_agent(llm=base_llm, tools=tools, prompt=prompt)

        # # Create agent executor with proper configuration
        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True,      
        )
        
        # try:
        #     test_result = search_conversation_history("test query", 1)
        #     print(f"Tool test result: {test_result[:100]}...")
        # except Exception as tool_error:
        #     print(f"Tool test failed: {tool_error}")
        
        # Execute agent with tools using try-catch for StopIteration
        print("Executing agent...")
        with get_openai_callback() as cb:
            try:
                result = await agent_executor.ainvoke(
                    {
                        "input": state["input_message"],
                        "short_messages": state["short_messages"]                
                    },  # Wrap in dict
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
            "messages": AIMessage(content=result["output"])
        }
        
    except Exception as e:
        print(f"Error in general_question: {str(e)}")
        
        # Fallback to simple response without tools
#         fallback_response = """I'm Maiden, your Tongits assistant. I can help you with questions about this Filipino card game. 
        
# Tongits is a three-player rummy game where you try to empty your hand or have the lowest points. Players form melds (sets/runs) and can hit others' melds or burn to end the round early."""
        
        return {
            **state,
            "messages": AIMessage(content=str(e))
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