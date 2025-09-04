from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import RunnableConfig
from llm.states import SharedState
from llm.node_intent_classifier import intent_classifier
from llm_model import checkpointer
from llm.node_general_question import general_question as node_general_question
from llm.node_fallback import fallback as node_fallback
from llm.node_save_conversation import save_conversation as node_save_conversation

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

    print(f"updated state: {current_state}")
    

    return current_state
    

def build_graph():
    """Build graph with proper looping"""

    graph = StateGraph(SharedState)

    # NODES
    graph.add_node("node_initializer", node_initializer)
    # graph.add_node("intent_classifier", intent_classifier)
    graph.add_node("node_intent_router", node_intent_router)
    graph.add_node("node_save_conversation", node_save_conversation)
    # EDGE
    graph.add_edge(START, "node_initializer")    
    # graph.add_edge("node_initializer", "intent_classifier")
    graph.add_edge("node_initializer", "node_intent_router")
    graph.add_edge("node_intent_router", "node_save_conversation")
    graph.add_edge("node_save_conversation", END)

    return graph.compile(checkpointer=checkpointer)