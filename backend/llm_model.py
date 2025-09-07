from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

LLM_MODEL = "llama3.2-vision:latest"
OLLAMA_BASE_URL = "http://localhost:11434" 
# LLM_MODEL = "gpt-oss:latest"
# OLLAMA_BASE_URL = "http://localhost:11435" 

LLM_TEMPERATURE = 0

def setup_persistence(persistence_type="memory"):
    """Setup persistence based on type"""
    if persistence_type == "memory":
        return MemorySaver()
    elif persistence_type == "sqlite":
        return SqliteSaver.from_conn_string("checkpoints.db")
    else:
        raise ValueError("persistence_type must be 'memory' or 'sqlite'")


# Module-level variables that will be initialized
base_llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE, base_url=OLLAMA_BASE_URL, num_ctx=8192, num_predict=4080)
checkpointer = setup_persistence()
