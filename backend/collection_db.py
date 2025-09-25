import chromadb
import fitz
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

GAME_COLLECTION_NAME = "TONGITS_RULES"
# Global variable to store the collection
collection = None
GAME_RULES_PATH = r"D:\development\stt\game_rules"
# Initialize ChromaDB
CHOROMA_PERSIST_PATH = Path(GAME_RULES_PATH) / "chroma_persist"
chroma_client = chromadb.PersistentClient(path=CHOROMA_PERSIST_PATH)
# Load local embedding model (free, no API key)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

json_filename = "tongits.jsonl"
JSON_PATH = Path(GAME_RULES_PATH) / json_filename

def initialize_chroma_collection():
    """Initialize the ChromaDB collection with JSONL data"""
    try:
        # Try to get existing collection
        collection = chroma_client.get_collection(name=GAME_COLLECTION_NAME)        
        return collection
    except chromadb.errors.NotFoundError:
        print("🔄 Creating new ChromaDB collection...")
        
        # Create new collection
        collection = chroma_client.create_collection(name=GAME_COLLECTION_NAME)
        
        # Load and process JSONL
        
        
        if not JSON_PATH.exists():
            raise FileNotFoundError(f"❌ JSONL file not found: {JSON_PATH.resolve()}")
        
        print(f"✅ JSONL found at: {JSON_PATH.resolve()}")
        
        docs = []
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            for line in f:
                docs.append(json.loads(line))
        
        # embedder = SentenceTransformer("all-MiniLM-L6-v2")
        
        # --- Step 2. Embed & store documents in Chroma ---
        for d in docs:
            text = f"Q: {d['question']} A: {d['answer']}"
            embedding = embedder.encode(text).tolist()
            
            collection.add(
                ids=[d["id"]],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{"category": d["category"]}]
            )

        return collection

def get_collection_game_rules():
    """Get the initialized collection"""
    global collection
    if collection is None:
        collection = initialize_chroma_collection()
    return collection