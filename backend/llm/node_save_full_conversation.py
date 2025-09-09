import chromadb
import uuid
from datetime import datetime
from llm.states import SharedState
from sentence_transformers import SentenceTransformer
from langchain_core.runnables import RunnableConfig
from collection_db import chroma_client, embedder

async def save_full_conversation(state: SharedState, config: RunnableConfig):
    """ Save full conversation here including AI Responses """

    thread_id = config.get("configurable",{}).get("thread_id") if config else None
    
    # Get or create collection with thread_id as name
    try:
        collection = chroma_client.get_collection(thread_id)
    except:
        collection = chroma_client.create_collection(thread_id)
    
    # Get messages from state
    messages = state.get("messages", [])
    
    if not messages:
        return state

    # Prepare data for ChromaDB AI Messages
    documents = []
    metadatas = []
    ids = []

    init_content = state["input_message"]
    init_meta = {
        "thread_id": thread_id,
        "message_type": "user",
        "timestamp": datetime.now().isoformat()        
    }
    init_id = f"{thread_id}_{datetime.now().timestamp()}_{uuid.uuid4()}"
   
    documents.append(init_content)
    metadatas.append(init_meta),
    ids.append(init_id)

    for message in messages:
        # Extract content from message
        if hasattr(message, 'content'):
            content = message.content
        else:
            content = str(message)
        
        # Skip empty messages
        if not content or content.strip() == "":
            continue
            
        # Create unique ID for this message
        message_id = f"{thread_id}_{datetime.now().timestamp()}_{uuid.uuid4()}"
        
        # Get message type (user/ai)
        message_type = getattr(message, 'type', 'unknown')
        
        # Create metadata
        metadata = {
            "thread_id": thread_id,
            "message_type": message_type,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to lists
        documents.append(content)
        metadatas.append(metadata)
        ids.append(message_id)
    
    # Add documents to collection if we have any
    if documents:
        # Generate embeddings using the embedder
        embeddings = [embedder.encode(doc).tolist() for doc in documents]

        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
        print(f"Saved {len(documents)} messages to ChromaDB collection: {thread_id}")
        