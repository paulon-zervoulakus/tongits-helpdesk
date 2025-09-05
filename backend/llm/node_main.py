import json
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import RunnableConfig
from llm.node_save_short_message import save_short_message as node_save_short_message
from llm.states import SharedState
from llm.node_intent_classifier import intent_classifier
from llm_model import checkpointer
from llm.node_general_question import general_question as node_general_question
from llm.node_fallback import fallback as node_fallback
from llm.node_save_full_conversation import save_full_conversation as node_save_full_conversation

async def node_initializer(state: SharedState) -> SharedState:
    """Node that initializes the state"""        
    return {
        **state
    }

async def node_intent_router(state: SharedState, config: RunnableConfig) -> SharedState:
    current_state = state
    
    # for i in state["intent"]:
    #     match i:
    #         case "general_question":
    #             current_state = await node_general_question(current_state)           
    #         case "fallback":            
    #             current_state = await node_fallback(current_state)      
    current_state["messages"] = []
    current_state = await node_general_question(current_state, config=config)           
    # test_tools(config=config)

    # print("State:")
    # print(json.dumps(current_state, indent=4, ensure_ascii=False, default=str))
    

    return current_state
    

def build_graph():
    """Build graph with proper looping"""

    graph = StateGraph(SharedState)

    # NODES
    graph.add_node("node_initializer", node_initializer)
    # graph.add_node("intent_classifier", intent_classifier)
    graph.add_node("node_intent_router", node_intent_router)
    graph.add_node("node_save_full_conversation", node_save_full_conversation)
    graph.add_node("node_save_short_message", node_save_short_message)
    # EDGE
    graph.add_edge(START, "node_initializer")    
    # graph.add_edge("node_initializer", "intent_classifier")
    graph.add_edge("node_initializer", "node_intent_router")
    graph.add_edge("node_intent_router", "node_save_full_conversation")
    graph.add_edge("node_intent_router", "node_save_short_message")
    graph.add_edge("node_save_full_conversation", END)
    graph.add_edge("node_save_short_message", END)

    return graph.compile(checkpointer=checkpointer)