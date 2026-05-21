from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownTextSplitter
from langchain_core.documents import Document


def get_recursive_splitter(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    separators: list[str] | None = None,
) -> RecursiveCharacterTextSplitter:
    separators = separators or ["\n\n", "\n", ". ", " ", ""]
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
    )


def get_markdown_splitter(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> MarkdownTextSplitter:
    return MarkdownTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def split_documents(
    documents: list[Document],
    splitter: RecursiveCharacterTextSplitter | None = None,
) -> list[Document]:
    if splitter is None:
        splitter = get_recursive_splitter()
    return splitter.split_documents(documents)


def split_with_overlap(
    documents: list[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    splitter = get_recursive_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(documents)