import json
import chromadb
from sentence_transformers import SentenceTransformer

# Load local embedding model (free, no API key)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize Chroma
chroma_client = chromadb.Client()
collection = chroma_client.create_collection("tongits_helpdesk")

# --- Step 1. Load your knowledge base JSONL ---
docs = []
with open("test.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        docs.append(json.loads(line))

for d in docs:
    print(d)