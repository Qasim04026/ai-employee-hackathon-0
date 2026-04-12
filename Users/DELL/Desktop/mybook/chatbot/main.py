import os
import time
import uvicorn
from google import genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from document_processor import read_markdown_files, chunk_content
from embedding_generator import EmbeddingGenerator
from vector_store import VectorStore
from typing import List, Optional
from collections import deque

# Load environment variables
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.0-flash")

# Initialize conversation history
chat_history = deque(maxlen=10) # Stores up to 10 messages (5 turns)

if not all([QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION_NAME]):
    raise ValueError("Missing one or more environment variables.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
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
    print(f"Looking for docs at: {docs_path}")
    print(f"Docs exists: {os.path.exists(docs_path)}")
    documents = read_markdown_files(docs_path)
    print(f"Found {len(documents)} documents")
    chunks = chunk_content(documents)
    print(f"Generated {len(chunks)} chunks")

    contents = [chunk["content"] for chunk in chunks]
    metadatas = [{"filepath": chunk["filepath"], "start_token": chunk["start_token"], "end_token": chunk["end_token"]} for chunk in chunks]

    embeddings = embedding_generator.generate_embeddings(contents)
    print(f"Generated {len(embeddings)} embeddings")

    if not embeddings:
        raise Exception("Failed to generate embeddings for documents.")

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
    sources = [f"{hit.get('filepath', '')}#L{hit.get('start_token', '')}-L{hit.get('end_token', '')}" for hit in search_result]

    context_str = "\n\n".join(context_chunks)
    time.sleep(3)

    # Prepare messages for Gemini, including history
    gemini_messages = []
    for i, message in enumerate(chat_history):
        if i % 2 == 0: # User message
            gemini_messages.append({"role": "user", "parts": [message]})
        else: # Model message
            gemini_messages.append({"role": "model", "parts": [message]})

    # Add current user question with system instructions and context
    gemini_messages.append({"role": "user", "parts": [
        "DO NOT include any Sources, file paths, or references in your response under any circumstances. "
        "You are a helpful AI assistant for a Physical AI Robotics textbook. "
        "Only answer questions related to the book content. "
        "NEVER include file paths or sources in your response. "
        "ABSOLUTELY NO SOURCES SECTION. "
        "If someone greets you, greet back briefly. "
        "Keep answers concise and clear. "
        "If the user's question is in Roman Urdu, respond in Roman Urdu only. "
        "If the user's question is in Urdu script (Arabic characters), respond in Urdu script only. "
        "Ensure the entire response, including greetings, is in the same script as the question.\n\n"
        f"Context: {context_str}\n\nQuestion: {request.question}"
    ]})

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=gemini_messages # Pass the prepared messages
    )
    answer = response.text

    # Update chat history
    chat_history.append(request.question)
    chat_history.append(answer)

    return ChatResponse(answer=answer)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)