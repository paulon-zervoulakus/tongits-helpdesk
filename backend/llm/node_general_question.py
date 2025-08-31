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

# Test function to verify tools work
# def test_tools(config: RunnableConfig):
#     """Test function to verify tools work independently"""

#     global global_thread_id 
#     global_thread_id = config.get("configurable", {}).get("thread_id")

#     print("Testing search_conversation_history...")
#     result1 = search_conversation_history.func("Paulo", 1)
#     print(f"Result 1: {result1}")
    
#     print("\nTesting game_ruling...")
#     result2 = game_ruling.func("how to win", 1)
#     print(f"Result 2: {result2}")
    
#     return result1, result2

def prompt_modifier():
    return """You are Crystal Maiden, a helpful assistant for the Filipino card game Tongits. Users can call you "Maiden."

You have access to the following tools:

{tools}

### IMPORTANT TOOL ARGUMENT RULES:
- Tool: search_conversation_history(query: str, filter_user: Optional[bool] = None, top_k: int = 3)
- `filter_user` meaning:
  * true = search only USER messages
  * false = search only AI responses
  * null (or omit) = search BOTH user and AI
- You MUST always decide one of these three when calling this tool:
  * If the user is asking about **what they said before**, set filter_user = true.
  * If the user is asking about **what you (Maiden) answered before**, set filter_user = false.
  * If the user’s intent is ambiguous, or they want **both perspectives**, set filter_user = null.

## PAGINATION RULES:
- Start with Action Input: {"top_k": 3, "offset": 0}
- If no relevant results found, retry ONCE with {"top_k": 3, "offset": 3}
- If still no info, then stop and answer "I couldn't find that information."

MANDATORY FORMAT - Follow this EXACTLY after each tool use:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
Thought: I now know the final answer
Final Answer: the final answer to the original input question

## CRITICAL POST-OBSERVATION RULES:

**AFTER getting an Observation, you MUST write EXACTLY:**
```
Thought: I now know the final answer
Final Answer: [your response using the observation data]
```

**DO NOT:**
- Try to use another tool after getting relevant results
- Write incomplete "Thought:" without "Final Answer:"
- Generate empty "Action:" lines
- Continue reasoning without proper format

## COMPLETION EXAMPLES:

**✅ CORRECT completion:**
Action: search_conversation_history
Action Input: food preferences besides Apple
Observation: Found: User mentioned "I like Banana more than eating Apple"
Thought: I now know the final answer
Final Answer: Yes, I remember! You mentioned that you love bananas. You said you like bananas more than eating apples.

**❌ WRONG (what you're experiencing):**
Observation: Found: User mentioned bananas
Thought: The user likes bananas...
[Missing Action/Final Answer - causes parsing error]

## EXPLICIT STOPPING INSTRUCTION:
When you receive an Observation that answers the user's question:
1. Write "Thought: I now know the final answer"
2. Write "Final Answer: [your response]"
3. STOP - do not generate anything else

## DECISION TREE AFTER OBSERVATION:
- Got relevant info? → "Thought: I now know the final answer" → "Final Answer:"
- Got no relevant info? → "Thought: I now know the final answer" → "Final Answer: I couldn't find that information"
- Completely unclear result? → Try ONE more tool, then Final Answer

## TEMPLATE FOR SUCCESS:
After ANY Observation, your next lines should ALWAYS be:
```
Thought: I now know the final answer
Final Answer: [response incorporating the observation]
```

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

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
            ("system", prompt_modifier()),
            ("human", "{input}"),
            ("assistant", "{agent_scratchpad}"),
        ])        

        agent = create_react_agent(llm=base_llm, tools=tools, prompt=prompt)

        # # Create agent executor with proper configuration
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            early_stopping_method="force"         
        )
        
        # try:
        #     test_result = search_conversation_history("test query", 1)
        #     print(f"Tool test result: {test_result[:100]}...")
        # except Exception as tool_error:
        #     print(f"Tool test failed: {tool_error}")
        
        # Execute agent with tools using try-catch for StopIteration
        print("Executing agent...")
        try:
            result = await agent_executor.ainvoke(
                {"input": state["input_message"]},  # Wrap in dict
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
        print(f"Result type: {type(result)}")
        print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        print(f"Result: {result}")
        print("**********************************")
        
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nTime check\n - after llm: general_question - time: {elapsed:.3f}")
        
        return {
            **state,
            "short_message": "node fallback with tools",
            "messages": state.get("messages", []) + [AIMessage(content=result["output"])]
        }
        
    except Exception as e:
        print(f"Error in general_question: {str(e)}")
        
        # Fallback to simple response without tools
#         fallback_response = """I'm Maiden, your Tongits assistant. I can help you with questions about this Filipino card game. 
        
# Tongits is a three-player rummy game where you try to empty your hand or have the lowest points. Players form melds (sets/runs) and can hit others' melds or burn to end the round early."""
        
        return {
            **state,
            "short_message": "node fallback - error occurred",
            "messages": state.get("messages", []) + [AIMessage(content=str(e))]
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