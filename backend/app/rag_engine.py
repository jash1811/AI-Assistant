import time

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings


class RAGEngine:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to backend/.env before starting the server."
            )

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
        )
        self.llm = ChatGoogleGenerativeAI(
            model=settings.CHAT_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.3,
        )
        # langchain-chroma persists automatically when persist_directory is set.
        self.vector_store = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            embedding_function=self.embeddings,
        )

    def process_document(self, file_path: str) -> int:
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        chunks = text_splitter.split_documents(documents)

        # Index in batches so we stay under the free-tier embedding rate limit,
        # retrying with back-off whenever the quota is briefly exceeded.
        batch_size = settings.EMBED_BATCH_SIZE
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            self._add_with_retry(batch)
            if start + batch_size < len(chunks):
                time.sleep(settings.EMBED_BATCH_PAUSE)

        return len(chunks)

    def _add_with_retry(self, batch, max_retries: int = 6) -> None:
        for attempt in range(max_retries):
            try:
                self.vector_store.add_documents(batch)
                return
            except Exception as exc:
                message = str(exc)
                is_rate_limit = "429" in message or "RESOURCE_EXHAUSTED" in message
                if is_rate_limit and attempt < max_retries - 1:
                    # Per-minute quota: wait a full window for it to reset.
                    time.sleep(settings.EMBED_BATCH_PAUSE)
                    continue
                raise

    def answer_query(self, query: str) -> dict:
        retriever = self.vector_store.as_retriever(
            search_kwargs={"k": settings.TOP_K}
        )

        system_prompt = (
            "You are an expert AI document assistant. Use the provided context to "
            "answer the question accurately. If the answer is not contained within "
            "the context, state clearly that you cannot find the answer in the document.\n\n"
            "Context:\n{context}"
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{input}"),
            ]
        )

        combine_docs_chain = create_stuff_documents_chain(self.llm, prompt)
        rag_chain = create_retrieval_chain(retriever, combine_docs_chain)

        response = rag_chain.invoke({"input": query})

        sources = [
            {
                "page": doc.metadata.get("page", 0) + 1,
                "content": doc.page_content[:150] + "...",
            }
            for doc in response.get("context", [])
        ]

        return {
            "answer": str(response["answer"]),
            "sources": sources,
        }

    def clear_index(self) -> None:
        """Delete every indexed passage and start with an empty store."""
        self.vector_store.delete_collection()
        self.vector_store = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            embedding_function=self.embeddings,
        )
