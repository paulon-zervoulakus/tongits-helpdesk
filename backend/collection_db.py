import chromadb
import fitz
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

GAME_COLLECTION_NAME = "TONGITS_RULES"
# Global variable to store the collection
collection = None
# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_persist")
# Load local embedding model (free, no API key)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

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
        jsonl_path = Path("../game_rules/tongits.jsonl")
        
        if not jsonl_path.exists():
            raise FileNotFoundError(f"❌ JSONL file not found: {jsonl_path.resolve()}")
        
        print(f"✅ JSONL found at: {jsonl_path.resolve()}")
        
        docs = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
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