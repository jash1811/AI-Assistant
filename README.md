# Enterprise RAG Document Q&A Platform

Upload a PDF, ask questions, get source-cited answers. Built with **FastAPI + LangChain + Google Gemini + ChromaDB** (backend) and **Vue 3 + Vite** (frontend).

## Prerequisites

- Python 3.11 or 3.12
- Node.js (installed ✅)
- A free Gemini API key: https://aistudio.google.com/apikey

## Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # PowerShell/cmd on Windows
pip install -r requirements.txt
```

Put your key in `backend/.env`:

```env
GEMINI_API_KEY=your_real_key_here
```

Run the API (from the `backend/` folder):

```bash
uvicorn app.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## How it works

1. Upload a PDF → text is split into overlapping chunks → embedded with Gemini → stored in ChromaDB.
2. Ask a question → the question is embedded, top-k similar chunks are retrieved → Gemini answers using only that context → sources (page + snippet) are returned.
