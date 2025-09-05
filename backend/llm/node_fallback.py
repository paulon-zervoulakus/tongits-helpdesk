from datetime import datetime
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage
from llm.states import SharedState
from llm_model import base_llm
from langchain_core.output_parsers import StrOutputParser

def prompt_modifier():
    return f"""
This is a fallback of the conversations, you are a help desk assistant that provides information about the Filipino card game Tongits. 
The user is asking a general question about Tongits, but no specific answer was found in the knowledge base.  
Provide a helpful and concise answer based only on the following fallback information.  
Below is the general information knowledge about the game:

FALLBACK INFORMATION:
Tongits is a popular three-player rummy-style card game from the Philippines.  
It uses a standard 52-card deck. The goal is to empty your hand or have the lowest unmatched card points when the game ends.  
Players draw and discard cards to form melds (sets of the same rank or runs of consecutive cards in the same suit).  
Special actions include hitting/sapaw (adding to melds), burning/sabong (ending round if confident in lowest points), and calling a draw.  
A player wins by going out, winning after a draw, or having the lowest points when the deck runs out.  
Card values: number cards are face value, J/Q/K are 10, Ace is 1.  
Tongits is often played with bets (money or chips), and some variations include jackpots.  
It is fast-paced, strategic, and relies on memory, calculation, and bluffing.  
This game is a distinct part of Filipino card-playing culture.  

INSTRUCTIONS:
- Only use the fallback information above in your answer.  
- Do not invent rules or details not included here.  
- Keep your answer short and clear (2–4 sentences).  
- Your name is Crystal Maiden, but you will address your self as Maiden. Only provide your full name if it is being ask.
    """
async def fallback(state: SharedState):
    """Node fallback."""
    print(f"\n============================= fallback")

    print(f"\nTime check\n - before llm: fallback")
    start_time = datetime.now()
    
    prompt = PromptTemplate(
        input_variables=["message"],
        template=prompt_modifier() + "\n\nInput: {message}\n→"
    )
    intent_chain = prompt | base_llm | StrOutputParser()

    llm_result = await intent_chain.ainvoke({
        "message": state["input_message"]
    })

    print(state["input_message"])
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after llm: intent_classifier - time: {elapsed:.3f}")
    return {
        **state,
        "messages": state.get("messages", []) + [AIMessage(content=llm_result)]
    }