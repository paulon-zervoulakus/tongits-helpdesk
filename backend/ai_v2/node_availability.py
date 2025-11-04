import json
from ai_v2.states import AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_react_agent
from llm_model import checkpointer, base_llm
from langchain_core.tools import tool

from model.events import Happenings
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from database import get_db
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda

def node_availability(state: AgentState, config: RunnableConfig) -> AgentState:
    """Handle event availability and scheduling inquiries."""
    
    # Check if this node should handle the request
    intents = state.get("intent", [])
    if "availability" not in intents:
        # This node doesn't handle this intent, return empty raw_messages
        return state
    
    AVAILABILITY_PROMPT = """You are a JSON data retrieval assistant that uses tools to find upcoming events. Follow the ReAct format exactly.

Use the following format:

Thought: You should always think about what you need to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now have the final result
Final Answer: [Return ONLY the raw JSON from the observation, nothing else]

CRITICAL RULES:
1. Always follow the exact format above with "Thought:", "Action:", "Action Input:", "Observation:"
2. After receiving tool results in Observation, your next step must be "Thought: I now have the final result"
3. Your Final Answer must ONLY contain the JSON data returned by the tool - no additional text
4. Do not interpret, summarize, or modify the JSON data in any way
5. Do not add conversational text like "Here are the events" or "I found X events"

TOOLS:
- You have access to the following tool(s): {tool_descriptions}

USERS MESSAGE:
{intent_phrases}

Begin!

Thought: I need to retrieve event data for this query"""

    try:
        intent_phrases = ",".join(
            [item.phrase_message for item in state["intent_list"] if item.intent == "availability"]
        )
        # Create availability tools
        # tools = [event_search_tool]
        tools = [event_search_tool]
        tool_descriptions = "\n".join(
            [f"- {t.name}: {t.description}" for t in tools]
        )

        # Create Marcus agent
        availability_prompt = ChatPromptTemplate.from_messages([
            ("system", AVAILABILITY_PROMPT),
            ("system","{agent_scratchpad}"),
            ("system","{tools}")
        ])
        agent = create_react_agent(
            llm=base_llm,
            tools=tools,
            prompt=availability_prompt
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
            # Execute availability agent
            start_time = datetime.now()
            result = agent_executor.invoke({
                "intent_phrases": intent_phrases,
                "tool_descriptions": tool_descriptions,
                "tools": ", ".join([t.name for t in tools]),
                "tool_names": ", ".join([t.name for t in tools])
            })      

            print("**********************************")
            print("--- node_availability ---")
            print(f"Prompt tokens: {cb.prompt_tokens}")
            print(f"Completion tokens: {cb.completion_tokens}")
            print(f"Total tokens: {cb.total_tokens}")
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\nTime spent node_availability: {elapsed:.3f}")            
            print("**********************************")
        
            return {
                **state,
                "raw_messages": state["raw_messages"].append(result.get("output"))
            }
        
    except Exception as e:
        print(f"Error in node_availability: {e}")
        
        # Fallback with helpful message
        error_raw_message = "I'm Marcus, your event coordinator! While I'm having a small technical issue accessing the latest schedule, I'd be happy to help you find the perfect Tongits event time. What days and times work best for you? I can check our calendar and get back to you with specific options!"
        
        return {
            **state,
            "raw_messages": state["raw_messages"].append(error_raw_message)
        }

@tool
def event_search_tool(query: str):
    """This tool will query the upcoming events
    
Args:
    query: string    
Returns:
String containing event information based on the query.
"""
    
    try:
        # Use your existing generator properly
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            events = search_happenings(db, query)

            if events:
                events_data = [e.to_dict() for e in events]
                return json.dumps(events_data, indent=2, default=str)
            else:
                return json.dumps([], indent=2)
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error in event_search_tool: {e}")
        return []
    
def search_happenings(db: Session, query: str) -> list:
    """Search the happenings table based on query keywords."""
    
    query_lower = query.lower()
    base_query = db.query(Happenings)
    
    # Time-based filters
    now = datetime.now()
    FUTURE_KEYWORDS = [
        "upcoming", "next", "future", "later", "soon", "coming", "ahead", "approaching", "in advance",
        "what’s next", "whats next", "coming up", "what’s coming", "whats coming", 
        "later on", "after this", "future events", "next schedule", 
        "next session", "next round", "next match", "what’s ahead", "whats ahead"
    ]

    # handle upcoming event logic

    if "today" in query_lower:
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        base_query = base_query.filter(
            and_(
                Happenings.date_of_event >= start_of_day,
                Happenings.date_of_event < end_of_day
            )
        )
    elif "tomorrow" in query_lower:
        tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        base_query = base_query.filter(
            and_(
                Happenings.date_of_event >= tomorrow_start,
                Happenings.date_of_event < tomorrow_end
            )
        )
    # elif "this week" in query_lower or "upcoming" in query_lower:
    #     week_end = now + timedelta(days=7)
    #     base_query = base_query.filter(
    #         and_(
    #             Happenings.date_of_event >= now,
    #             Happenings.date_of_event <= week_end
    #         )
    #     )
    # elif "next week" in query_lower:
    #     week_start = now + timedelta(days=7)
    #     week_end = week_start + timedelta(days=7)
    #     base_query = base_query.filter(
    #         and_(
    #             Happenings.date_of_event >= week_start,
    #             Happenings.date_of_event <= week_end
    #         )
    #     )
    elif any(word in query_lower for word in FUTURE_KEYWORDS):
        base_query = base_query.filter(Happenings.date_of_event >= now)
        
        # Default to future events
        
    # Debug: Print the query results before content-based filtering
    # results = base_query.all()
    # print(f"[Debug] - Found {len(results)} events after date filter:")
    # for event in results:
    #     print(f"Event: {event.title} on {event.date_of_event}")
    
    # Content-based search (title, description)
    search_terms = ["tournament", "beginner", "workshop", "social", "casual", "competition"]
    
    for term in search_terms:
        if term in query_lower:
            base_query = base_query.filter(
                or_(
                    Happenings.title.ilike(f"%{term}%"),
                    Happenings.description.ilike(f"%{term}%")
                )
            )
            break  # Use first matching term
    
    # Execute query and return results
    return base_query.order_by(Happenings.date_of_event).limit(5).all()

# def format_events_for_persuasion(events: list) -> str:
#     """Format events in a persuasive way using actual database data."""
    
#     if not events:
#         return "No specific events found, but we have regular Tongits sessions! Let me get you the latest schedule."
    
#     formatted_events = []
    
#     for event in events:
#         # Format date nicely
#         if event.date_of_event:
#             formatted_date = event.date_of_event.strftime("%A, %B %d at %I:%M %p")
#         else:
#             formatted_date = "Date TBD"
        
#         # Build event description
#         event_desc = f"'{event.title}' on {formatted_date}"
        
#         if event.description:
#             # Truncate description if too long
#             desc = event.description[:100] + "..." if len(event.description) > 100 else event.description
#             event_desc += f" - {desc}"
        
#         if event.organizer:
#             event_desc += f" (Organized by {event.organizer})"
        
#         formatted_events.append(event_desc)
    
#     # Add persuasive intro
#     if len(events) == 1:
#         intro = "Perfect! Here's an exciting event coming up:"
#     else:
#         intro = f"Great! I found {len(events)} exciting events:"
    
#     return f"{intro} " + " | ".join(formatted_events)