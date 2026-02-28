"""
RAG (Retrieval-Augmented Generation) package.

    pinecone_store   Pinecone vector store — upsert and query
    retriever        High-level RAG context helper for agents
    langchain_rag    LangChain ConversationalRetrievalChain via Pinecone
"""

from .retriever import get_rag_context, should_use_rag
from .pinecone_store import upsert_documents, query_similar
from .langchain_rag import get_langchain_retriever, get_qa_chain, invoke_chain

__all__ = [
    "get_rag_context",
    "should_use_rag",
    "upsert_documents",
    "query_similar",
    "get_langchain_retriever",
    "get_qa_chain",
    "invoke_chain",
]
