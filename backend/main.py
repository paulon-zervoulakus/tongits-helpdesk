import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_route
from routes.audio import router as audio_route
from routes.auth import router as auth_route
from routes.public import router as pub_route
from contextlib import asynccontextmanager
from database import init_db
from collection_db import initialize_chroma_collection
# from llm_model import init_model

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_chroma_collection()
    init_db()
    # init_model()
    yield

app = FastAPI(
    title="Help Desk",
    description="A secure AI integration help desk",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc
    openapi_url="/openapi.json"  # OpenAPI spec
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"]
)

app.include_router(chat_route)
app.include_router(audio_route)
app.include_router(auth_route)
app.include_router(pub_route)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )