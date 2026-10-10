import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Model configuration (current free-tier Gemini models)
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gemini-3.8-flash")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

    # Storage
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")

    # Retrieval / chunking
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "2000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K: int = int(os.getenv("TOP_K", "4"))

    # Embedding rate limits (free tier allows ~100 requests/minute)
    EMBED_BATCH_SIZE: int = int(os.getenv("EMBED_BATCH_SIZE", "50"))
    EMBED_BATCH_PAUSE: int = int(os.getenv("EMBED_BATCH_PAUSE", "60"))


settings = Settings()
