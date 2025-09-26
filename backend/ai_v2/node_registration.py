from langchain_core.prompts import ChatPromptTemplate
from ai_v2.states import AgentState
from langchain_core.runnables import RunnableConfig


def node_registration(state: AgentState, config: RunnableConfig) -> AgentState:
    """Handles user registration in 2 steps: info collection + confirmation."""

    reg_form = {
        "fullname": state.get("fullname"),
        "email": state.get("email"),
        "nickname": state.get("nickname")
    }

    # Step 1: Collect missing info
    if not all(reg_form.values()):
        missing = [k for k, v in reg_form.items() if not v]
        output = (
            f"I’d love to secure your spot 🎉.\n"
            f"Could you provide your {', '.join(missing)}?"
        )
        state["stage"] = "registration"

    # Step 2: Ask for confirmation
    if all(reg_form.values()) and not state.get("confirmed", False):
        output = (
            f"Great! I have your details:\n"
            f"- Name: {reg_form['fullname']} ({reg_form['nickname']})\n"
            f"- Email: {reg_form['email']}\n"
            "Can I confirm your registration now? ✅"
        )
        state["stage"] = "confirmation"

    # Step 3: Save to DB after confirmation
    if all(reg_form.values()) and state.get("confirmed", False):
        output = (
            f"Perfect {reg_form['fullname']}! 🎉 "
            f"A confirmation email has been sent to {reg_form['email']}."
        )
        state["registered"] = True
        state["stage"] = "done"

        # 👉 DB save happens here
        # save_to_db(reg_form)

    return {
        **state,
        "raw_messages":  state["raw_messages"].append(output)
    }
