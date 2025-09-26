from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage 
from llm_model import checkpointer
from ai_v2.states import AgentState
from utils.cleaner import clean_transcript

# from ai_v2.tools import update_userform, game_rules

from ai_v2.node_classify_intent import node_classify_intent
from ai_v2.node_game_ruling import node_game_ruling
from ai_v2.node_availability import node_availability
# from ai_v2.node_persuasion import node_persuasion
from ai_v2.node_consolidator_manager import node_consolidator_manager
from ai_v2.node_neutral import node_neutral
from ai_v2.node_registration import node_registration
from ai_v2.node_msg_summarizer import node_msg_summarizer

def preprocess(state: AgentState) -> AgentState:
    """Clean transcript + classify intent."""    
    cleaned = clean_transcript(state["input_message"])    
    state["input_message"] = cleaned    
    state["messages"] = HumanMessage(content=cleaned)   
    return state

def intent_router(state: AgentState):
    """Return multiple next nodes to fan-out in parallel."""
    return ["node_availability", "node_game_ruling", "node_neutral", "node_registration"]

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("preprocess", preprocess)
    graph.add_node("node_classify_intent", node_classify_intent)

    graph.add_node("node_neutral", node_neutral)
    graph.add_node("node_game_ruling", node_game_ruling)
    graph.add_node("node_availability", node_availability) 
    graph.add_node("node_registration", node_registration)
    graph.add_node("node_consolidator_manager", node_consolidator_manager)
    graph.add_node("node_msg_summarizer", node_msg_summarizer)

    graph.add_edge(START, "preprocess")
    graph.add_edge("preprocess", "node_classify_intent")

    # Proper fan-out (parallel execution)
    graph.add_conditional_edges("node_classify_intent", intent_router)

    graph.add_edge("node_neutral", "node_consolidator_manager")
    graph.add_edge("node_game_ruling", "node_consolidator_manager")
    graph.add_edge("node_availability", "node_consolidator_manager")
    graph.add_edge("node_registration", "node_consolidator_manager")

    # End
    graph.add_edge("node_consolidator_manager", "node_msg_summarizer")
    graph.add_edge("node_msg_summarizer", END)

    return graph.compile(checkpointer=checkpointer)