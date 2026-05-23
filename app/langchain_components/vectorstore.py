import asyncio

from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.db.chroma import get_chroma_client, get_chroma_collection
from app.langchain_components.embeddings import OpenRouterEmbeddings


def _normalize_where(where: dict | None) -> dict | None:
    """Normalize metadata filters for Chroma.

    Chroma expects the top-level `where` to contain either a single field condition
    or a single operator like `$and`/`$or`. When we want to apply multiple equality
    constraints, we wrap them in `$and`.
    """

    if not where:
        return None

    # If caller already provided an operator-based query, pass through unchanged.
    if any(str(key).startswith("$") for key in where.keys()):
        return where

    if len(where) <= 1:
        return where

    return {"$and": [{key: value} for key, value in where.items()]}


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
    ids = [
        (d.metadata.get("chunk_id") or d.metadata.get("id"))
        for d in documents
    ]
    if all(ids):
        return vectorstore.add_documents(documents, ids=ids)  # type: ignore[arg-type]
    return vectorstore.add_documents(documents)


async def aadd_documents(
    documents: list[Document],
    embeddings: OpenRouterEmbeddings | None = None,
) -> list[str]:
    vectorstore = get_vectorstore(embeddings)

    ids = [
        (d.metadata.get("chunk_id") or d.metadata.get("id"))
        for d in documents
    ]
    use_ids = all(ids)

    aadd = getattr(vectorstore, "aadd_documents", None)
    if callable(aadd):
        if use_ids:
            return await aadd(documents, ids=ids)  # type: ignore[arg-type]
        return await aadd(documents)

    if use_ids:
        return await asyncio.to_thread(vectorstore.add_documents, documents, ids)
    return await asyncio.to_thread(vectorstore.add_documents, documents)


def similarity_search(
    query: str,
    top_k: int = 5,
    embeddings: OpenRouterEmbeddings | None = None,
    where: dict | None = None,
) -> list[tuple[Document, float]]:
    vectorstore = get_vectorstore(embeddings)
    where = _normalize_where(where)
    try:
        return vectorstore.similarity_search_with_score(query, k=top_k, filter=where)
    except TypeError:
        return vectorstore.similarity_search_with_score(query, k=top_k)


async def asimilarity_search(
    query: str,
    top_k: int = 5,
    embeddings: OpenRouterEmbeddings | None = None,
    where: dict | None = None,
) -> list[tuple[Document, float]]:
    vectorstore = get_vectorstore(embeddings)
    where = _normalize_where(where)

    asearch = getattr(vectorstore, "asimilarity_search_with_score", None)
    if callable(asearch):
        try:
            return await asearch(query, k=top_k, filter=where)
        except TypeError:
            return await asearch(query, k=top_k)

    def _run():
        try:
            return vectorstore.similarity_search_with_score(query, k=top_k, filter=where)
        except TypeError:
            return vectorstore.similarity_search_with_score(query, k=top_k)

    return await asyncio.to_thread(_run)


def get_retriever(embeddings: OpenRouterEmbeddings | None = None, top_k: int = 5):
    vectorstore = get_vectorstore(embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": top_k})