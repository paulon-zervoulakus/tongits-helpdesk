import json
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from ai_v2.states import AgentState
from langchain_core.runnables import RunnableConfig
from llm_model import base_llm
from langchain_community.callbacks.manager import get_openai_callback

def node_registration(state: AgentState, config: RunnableConfig) -> AgentState:
    """Handles user registration with Clear Extraction and State Update Workflow"""

    intents = state.get("intent", [])
    if "registration" not in intents:
        return state  # This node doesn't handle other intents

    # Existing registration form data
    reg_form = {
        "fullname": state.get("fullname",""),
        "email": state.get("email",""),
        "nickname": state.get("nickname",""),
        "event_details": state.get("event_details","")
    }

    # Collect registration intent-related phrase messages    
    intent_phrases = ",".join(
        [item.phrase_message for item in state["intent_list"] if item.intent == "registration"]
    )

    PROMPT_INSTRUCTION = """Your role is to identify and extract information from the user's message. Your response will be a strict JSON format.

KEYPOINTS TO LOOK AT:
- Giving information such as fullname, nickname, or email that are used to identify the user for event registration.
- User is acknowledging confirmation to join the event.
- Provides information to update existing user details.

INFORMATION EXTRACTION RULES:
- ALWAYS extract any registration information (fullname, email, nickname) from the user's phrase messages
- Please be cautious when distinguishing between fullname and nickname to avoid confusion
- If user provides new information, use that new information even if existing form has different values
- Combine existing form data with newly extracted information from the user's phrase
- If user doesn't provide specific information, keep the existing form values
- DO NOT ask for or include any payment, billing, or financial information. 
- Registration refers ONLY to signing up for events, NOT any financial or account-related processes.
- **EVENT EXTRACTION RULE**: Extract ONLY the specific event that the user mentions or shows interest in from their message. Do NOT include multiple events unless the user explicitly asks about multiple events.

IMPORTANT: Never request or include payment, billing, or financial information of any kind.
This system only handles event sign-up details such as name, nickname, and email.

WORKFLOW TO FOLLOW:
- You MUST identify if the user is confirming registration or updating user information.
- FIRST: Extract any information from {{intent_phrases}} and {{conversation_summary}}, get users information or/and event information details.
- If the user is confirming registration:
    > If the form is INCOMPLETE (missing nickname), respond with:
      {{"registration": "Incomplete", "nickname":"[existing or extracted nickname]", "event_details":"[existing or extracted complete event information and base from the conversation_summary]"}}
    > If the form is COMPLETE and the user confirms registration, respond with:
      {{"registration":"Complete", "nickname":"[existing or extracted nickname]", "event_details":"[existing or extracted complete event information and base from the conversation_summary]"}}
- If the user is providing or updating information:
    > Extract and merge information, then respond with:
      {{"registration":"Updating", "fullname":"[merged fullname]", "email":"[merged email]", "nickname":"[merged nickname]", "event_details":"[existing or extracted complete event information and base from the conversation_summary]"}}

EXTRACTION EXAMPLES:
- "My nickname is Pau" → extract nickname: "Pau"
- "I'm John Smith" → extract fullname: "John Smith"
- "My email is john@example.com" → extract email: "john@example.com"
- "I'm Pau, can I join?" → extract nickname: "Pau"
- "I like to join the finals" → extract ONLY finals details
- "I want to join Dota Game Night" → extract ONLY Dota Game Night details

EXISTING REGISTRATION FORM:
{reg_form}

NOTE: You can use both the user's phrase messages and {{conversation_summary}} to inform your extraction and decisions.

Phrase messages:
{intent_phrases}

Summary of conversation:
{conversation_summary}

Respond *ONLY* with valid JSON in the described formats. No additional text or explanation.
"""
    
    try:
    
        chain = ChatPromptTemplate.from_template(PROMPT_INSTRUCTION) | base_llm 

        with get_openai_callback() as cb:
            start_time = datetime.now()
            response = chain.invoke({
                "reg_form": json.dumps(reg_form),
                "intent_phrases": intent_phrases,
                "conversation_summary": state.get("short_message","")
            })
            elapsed = (datetime.now() - start_time).total_seconds()
            
            print("**********************************")        
            print("--- node_registration ---")
            print(f"Prompt tokens: {cb.prompt_tokens}")
            print(f"Completion tokens: {cb.completion_tokens}")
            print(f"Total tokens: {cb.total_tokens}")
            print(f"\nTime spent node_registration: {elapsed:.3f}")    
            print("**********************************")

        # Parse response JSON
        response_data = json.loads(response.content if hasattr(response, 'content') else str(response))

        fullname = response_data.get("fullname", reg_form["fullname"])
        email = response_data.get("email", reg_form["email"])
        nickname = response_data.get("nickname", reg_form["nickname"])
        event_details = response_data.get("event_details", reg_form["event_details"])

        output = ""
        # Check if any required detail is missing
        missing_details = []
        if not fullname:
            missing_details.append("fullname")
        if not email:
            missing_details.append("email")
        if not nickname:
            missing_details.append("nickname")
        if not event_details:
            missing_details.append("event_details")

        if missing_details:
            # Output for incomplete form due to missing required details
            output = (
                f"I’d love to secure your spot 🎉.\n"
                f"Could you please provide your {', '.join(missing_details)}?"
            )
            state["stage"] = "registration"
            # Optionally update state with the data we have so far
            state.update({
                "fullname": fullname,
                "email": email,
                "nickname": nickname,
                "event_details": event_details
            })
        else:
            # React to registration status
            if response_data.get("registration") == "Complete":
                state.update({
                    "stage": "done",
                    "fullname": fullname,
                    "email": email,
                    "nickname": nickname,
                    "event_details": event_details
                })
                output = (
                    f"Perfect {fullname}! 🎉\n"
                    f"A confirmation email has been sent to {email}.\n"
                    f"It's nice to have you, {nickname}\n"
                    f"Here is the details:\n {event_details}\n"
                )
                # 👉 DB save could be here: save_to_db(state)

            # elif response_data.get("registration") == "Incomplete":
            #     missing = [k for k in ["fullname", "email", "nickname"] if not reg_form.get(k)]
            #     output = (
            #         f"I’d love to secure your spot 🎉.\n"
            #         f"Could you provide your {', '.join(missing)}?"
            #     )
            #     state["stage"] = "registration"

            elif response_data.get("registration") == "Updating":
                state.update({
                    "fullname": fullname,
                    "email": email,
                    "nickname": nickname,
                    "event_details": event_details,
                    "stage": "confirmation"
                })
                output = (
                    f"Great! Now that I have your details:\n"
                    f"- Name: {fullname} ({nickname})\n"
                    f"- Email: {email}\n"
                    f"- Happening: {event_details}\n\n"
                    "Can I confirm your registration now? ✅"
                )
            else:
                output = "Sorry, I couldn't understand your registration input. Could you please rephrase?"

        return {
            **state,
            "raw_messages": state["raw_messages"].append(output)
        }

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        print(f"Error in node_registration: {e}")
        return state
