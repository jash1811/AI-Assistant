import os
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.rag_engine import RAGEngine
from app.config import settings

app = FastAPI(title="Enterprise RAG Document Q&A API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
rag = RAGEngine()


class QueryRequest(BaseModel):
    question: str


@app.get("/")
async def health():
    return {"status": "ok", "chat_model": settings.CHAT_MODEL}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chunks_count = rag.process_document(file_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {exc}")

    return {
        "filename": file.filename,
        "status": "Processed successfully",
        "chunks_indexed": chunks_count,
    }


@app.post("/query")
async def query_document(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = rag.answer_query(request.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")

    return result


@app.post("/reset")
async def reset_index():
    try:
        rag.clear_index()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not clear documents: {exc}")

    return {"status": "cleared"}
