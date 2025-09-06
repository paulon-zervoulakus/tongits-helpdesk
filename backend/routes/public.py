from fastapi import APIRouter
from collection_db import chroma_client

router = APIRouter(prefix="/vector", tags=["vectordb"])


@router.get("/list")
async def list_all():
    collections = chroma_client.list_collections()
    results = []

    for col in collections:

        if col.name != "105844535472250345057":
            continue

        # Fetch documents & metadata for each collection
        items = col.get(include=["documents", "metadatas"])

        col_data = {
            "collection": col.name,
            "total_items": len(items["ids"]),
            "items": []
        }

        for idx, doc in enumerate(items["documents"], start=1):
            meta = items["metadatas"][idx - 1]
            col_data["items"].append({
                "id": items["ids"][idx - 1],
                "document": doc,
                "metadata": meta
            })

        results.append(col_data)

    return {"collections": results}
