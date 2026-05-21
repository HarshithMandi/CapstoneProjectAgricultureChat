import asyncio

from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.db.chroma import get_chroma_client, get_chroma_collection
from app.langchain_components.embeddings import OpenRouterEmbeddings


def get_vectorstore(embeddings: OpenRouterEmbeddings | None = None) -> Chroma:
    if embeddings is None:
        embeddings = OpenRouterEmbeddings()

    collection = get_chroma_collection()
    return Chroma(
        client=get_chroma_client(),
        collection_name=collection.name,
        embedding_function=embeddings,
    )


def add_documents(
    documents: list[Document],
    embeddings: OpenRouterEmbeddings | None = None,
) -> list[str]:
    vectorstore = get_vectorstore(embeddings)
    return vectorstore.add_documents(documents)


async def aadd_documents(
    documents: list[Document],
    embeddings: OpenRouterEmbeddings | None = None,
) -> list[str]:
    vectorstore = get_vectorstore(embeddings)

    aadd = getattr(vectorstore, "aadd_documents", None)
    if callable(aadd):
        return await aadd(documents)

    return await asyncio.to_thread(vectorstore.add_documents, documents)


def similarity_search(
    query: str,
    top_k: int = 5,
    embeddings: OpenRouterEmbeddings | None = None,
) -> list[tuple[Document, float]]:
    vectorstore = get_vectorstore(embeddings)
    return vectorstore.similarity_search_with_score(query, k=top_k)


async def asimilarity_search(
    query: str,
    top_k: int = 5,
    embeddings: OpenRouterEmbeddings | None = None,
) -> list[tuple[Document, float]]:
    vectorstore = get_vectorstore(embeddings)

    asearch = getattr(vectorstore, "asimilarity_search_with_score", None)
    if callable(asearch):
        return await asearch(query, k=top_k)

    return await asyncio.to_thread(vectorstore.similarity_search_with_score, query, k=top_k)


def get_retriever(embeddings: OpenRouterEmbeddings | None = None, top_k: int = 5):
    vectorstore = get_vectorstore(embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": top_k})