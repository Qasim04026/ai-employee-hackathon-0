import os
import time
import uvicorn
from google import genai
from google.genai import types
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from document_processor import read_markdown_files, chunk_content
from embedding_generator import EmbeddingGenerator
from vector_store import VectorStore
from typing import List, Optional
from collections import deque

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.0-flash")

chat_history = deque(maxlen=10)

if not all([QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION_NAME]):
    raise ValueError("Missing one or more environment variables.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embedding_generator = EmbeddingGenerator()
vector_store = VectorStore()

class ChatRequest(BaseModel):
    question: str
    selected_text: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str

class IngestResponse(BaseModel):
    message: str

def ingest_documents():
    docs_path = "docs/"
    documents = read_markdown_files(docs_path)
    chunks = chunk_content(documents)
    contents = [chunk["content"] for chunk in chunks]
    metadatas = [
        {
            "filepath": chunk["filepath"],
            "start_token": chunk["start_token"],
            "end_token": chunk["end_token"]
        }
        for chunk in chunks
    ]
    embeddings = embedding_generator.generate_embeddings(contents)
    if not embeddings:
        raise Exception("Failed to generate embeddings.")
    vector_store.recreate_collection()
    vector_store.upsert_vectors(contents, embeddings, metadatas)

@app.post("/ingest", response_model=IngestResponse)
async def ingest_content():
    try:
        ingest_documents()
        return IngestResponse(message="Content ingested successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_embedding(text: str) -> List[float]:
    embeddings = embedding_generator.generate_embeddings([text])
    if embeddings:
        return embeddings[0]
    raise Exception("Failed to generate embedding.")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest):
    query_text = request.question
    if request.selected_text:
        query_text = f"Context: {request.selected_text}\nQuestion: {request.question}"

    query_embedding = create_embedding(query_text)
    search_result = vector_store.search_vectors(query_embedding)
    context_chunks = [hit["content"] for hit in search_result]
    context_str = "\n\n".join(context_chunks)

    contents: list[types.Content] = []

    for i, msg in enumerate(chat_history):
        role = "user" if i % 2 == 0 else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=str(msg))]
            )
        )

    current_prompt = (
        f"Context from textbook:\n{context_str}\n\n"
        f"Question: {request.question}"
    )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=current_prompt)]
        )
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are a helpful AI assistant for a Physical AI and Humanoid Robotics textbook. "
                "Only answer questions related to the textbook content. "
                "NEVER include file paths, sources, or document references in your response. "
                "Keep answers concise and clear. "
                "If the user greets you, greet back briefly. "
                "Language detection rule: "
                "If the question contains Urdu script characters (like ا ب پ ت ٹ ث ج چ), "
                "respond ONLY in Urdu script. "
                "If the question is in Roman Urdu (like robot kya hai), "
                "respond ONLY in Roman Urdu. "
                "If the question is in English, respond in English. "
                "Never mix languages."
            )
        )
    )

    answer = response.text

    if "Sources:" in answer:
        answer = answer[:answer.index("Sources:")].strip()
    if "sources:" in answer.lower():
        answer = answer[:answer.lower().index("sources:")].strip()

    chat_history.append(request.question)
    chat_history.append(answer)

    return ChatResponse(answer=answer)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)