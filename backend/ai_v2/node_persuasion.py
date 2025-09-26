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

def node_persuasion(state: AgentState) -> AgentState:
    """Handle persuasion and general conversation to encourage event participation."""
    
    # Check if this node should handle the request
    intents = state.get("intent", [])
    if "neutral" not in intents:
        # This node doesn't handle this intent, return empty raw_messages
        return state
    
    PERSUASION_PROMPT = """Your role is to synthesize a persuasive response encouraging users to join Tongits events.

PERSUASION TECHNIQUES:
- Social proof: "Many players like you have joined and loved it!"
- Benefits: Fun, learning, meeting people, prizes, improving skills
- Personal connection: Ask about interests and connect to events
- Enthusiasm: Show genuine excitement about Tongits and events

CONTEXT AWARENESS:
- Use the conversation summary to understand what has been discussed previously
- Build upon previous conversations naturally without repeating information
- Reference past interactions to create a more personalized experience
- If the summary shows the user has already expressed interest, acknowledge that and build momentum

Goal: Create an enthusiastic, friendly response that guides users toward joining events.

---

User message: {user_message}

Conversation summary: {conversation_summary}

Synthesize response:"""

    try:        
        intent_phrases = ",".join([item.phrase_message for item in state.get("intent_list", []) if item.intent == "neutral"])
        # Create persuasion tools 
        
        # Create Elena agent
        persuasion_prompt = ChatPromptTemplate.from_messages([
            ("system", PERSUASION_PROMPT)        
        ])
        chain = persuasion_prompt | base_llm
        
        with get_openai_callback() as cb:
            start_time = datetime.now()
            # Execute persuasion agent
            print("**********************************")

            try:
                llm_output = chain.invoke({
                    "user_message": intent_phrases,
                    "conversation_summary": state.get("short_message","")
                })      
                ai_msg = AIMessage(content=llm_output.content)   

            except Exception as e:
                # LangGraph provides more specific exception types
                print(e)
                ai_msg = AIMessage(content="I need a more specific question to help you.")
               
            print(f"Prompt tokens: {cb.prompt_tokens}")
            print(f"Completion tokens: {cb.completion_tokens}")
            print(f"Total tokens: {cb.total_tokens}")
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\nTime spent: {elapsed:.3f}")            
            print("**********************************")

            return {
                **state,
                "raw_messages": [ai_msg]
            }
        
    except Exception as e:
        print(f"Error in node_persuasion: {e}")
        
        # Fallback with persuasive message
        error_raw_message = {
            "node_type": "persuasion",
            "agent_name": "Elena",
            "intent_handled": "neutral",
            "content": "Hey there! I'm Elena, and I'm excited about our upcoming Tongits events. Even though I had a small technical hiccup, I'd still love to chat about getting you involved in our amazing gaming community! What brings you here today?",
            "status": "error",
            "error": str(e)
        }
        
        return {
            **state,
            "raw_messages": [error_raw_message]
        }

# @tool
# def event_search_tool(query: str) -> str:
#     """Search for Tongits events to support persuasion efforts."""
#     try:
#         # Replace with your actual event search implementation
#         # This should search your events database/calendar
#         events = search_tongits_events(query)  # Your implementation
        
#         if events:
#             # Format events in a persuasive way
#             event_descriptions = []
#             for event in events[:3]:  # Top 3 events
#                 event_descriptions.append(
#                     f"'{event['name']}' on {event['date']} - {event['description']} "
#                     f"({event['spots_available']} spots left!)"
#                 )
#             return f"Found exciting events: " + "; ".join(event_descriptions)
#         else:
#             return "No specific events found, but we regularly host Tongits sessions with prizes and social activities!"
            
#     except Exception as e:
#         return "We have amazing Tongits events happening regularly! Great prizes, friendly community, and lots of fun. Perfect for all skill levels!"

@tool
def event_search_tool(query: str) -> str:
    """Search for Tongits events to support persuasion efforts.
    Args:
        query: string
    
    Returns:
        String containing the most relevant event information   
    """
    
    try:
        # Use your existing generator properly
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            events = search_happenings(db, query)
            
            if events:
                return format_events_for_persuasion(events)
            else:
                return "We have exciting Tongits events coming up! Let me check our calendar and get back to you with specific dates and details."
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error in event_search_tool: {e}")
        return "We regularly host amazing Tongits events with great prizes and community atmosphere! Perfect for all skill levels!"
    
def search_happenings(db: Session, query: str) -> list:
    """Search the happenings table based on query keywords."""
    
    query_lower = query.lower()
    base_query = db.query(Happenings)
    
    # Time-based filters
    now = datetime.now()
    
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
    elif "this week" in query_lower or "upcoming" in query_lower:
        week_end = now + timedelta(days=7)
        base_query = base_query.filter(
            and_(
                Happenings.date_of_event >= now,
                Happenings.date_of_event <= week_end
            )
        )
    elif "next week" in query_lower:
        week_start = now + timedelta(days=7)
        week_end = week_start + timedelta(days=7)
        base_query = base_query.filter(
            and_(
                Happenings.date_of_event >= week_start,
                Happenings.date_of_event <= week_end
            )
        )
    else:
        # Default to future events
        base_query = base_query.filter(Happenings.date_of_event >= now)
        
    # # Debug: Print the query results before content-based filtering
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

def format_events_for_persuasion(events: list) -> str:
    """Format events in a persuasive way using actual database data."""
    
    if not events:
        return "No specific events found, but we have regular Tongits sessions! Let me get you the latest schedule."
    
    formatted_events = []
    
    for event in events:
        # Format date nicely
        if event.date_of_event:
            formatted_date = event.date_of_event.strftime("%A, %B %d at %I:%M %p")
        else:
            formatted_date = "Date TBD"
        
        # Build event description
        event_desc = f"'{event.title}' on {formatted_date}"
        
        if event.description:
            # Truncate description if too long
            desc = event.description[:100] + "..." if len(event.description) > 100 else event.description
            event_desc += f" - {desc}"
        
        if event.organizer:
            event_desc += f" (Organized by {event.organizer})"
        
        formatted_events.append(event_desc)
    
    # Add persuasive intro
    if len(events) == 1:
        intro = "Perfect! Here's an exciting event coming up:"
    else:
        intro = f"Great! I found {len(events)} exciting events:"
    
    return f"{intro} " + " | ".join(formatted_events)

