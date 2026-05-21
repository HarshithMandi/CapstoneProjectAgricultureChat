from langchain_core.documents import Document
from app.langchain_components.splitters import get_recursive_splitter, split_documents
from app.langchain_components.documents import create_document
from app.utils.ids import generate_document_id

import re


class ChunkingService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = get_recursive_splitter(chunk_size, chunk_overlap)

        # Heuristic safety caps for large PDFs / long reports.
        self.max_section_chunks = 120
        self.max_paragraph_chunks = 400
        self.min_paragraph_chars = 80

        # Safety limit to avoid embeddings API max token errors.
        # This is an approximate chars-based guard; we still split via the recursive splitter.
        self.max_chunk_chars = 12000

    def chunk_text(
        self,
        text: str,
        metadata: dict,
        doc_id: str | None = None,
    ) -> list[Document]:
        doc_id = doc_id or generate_document_id()
        doc = create_document(text, metadata, doc_id=doc_id)
        chunks = split_documents([doc], self.splitter)

        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata.setdefault("chunk_type", "semantic")
            chunk.metadata["chunk_id"] = f"{doc_id}_{chunk.metadata['chunk_type']}_{i}"

        return chunks

    def chunk_text_multigranular(
        self,
        text: str,
        metadata: dict,
        doc_id: str | None = None,
    ) -> list[Document]:
        """Create multiple chunk representations for retrieval.

        - `section`: larger chunks aligned to headings/numbered sections
        - `paragraph`: small precise chunks
        - `semantic`: overlap chunks for general semantic search
        """

        doc_id = doc_id or generate_document_id()
        text = (text or "").strip()
        if not text:
            return []

        all_chunks: list[Document] = []

        # 1) Sections
        sections = self._split_into_sections(text)
        for i, sec in enumerate(sections[: self.max_section_chunks]):
            section_text = sec["content"].strip()
            if not section_text:
                continue
            md = {
                **metadata,
                "chunk_type": "section",
                "section_index": i,
                "section_title": sec.get("title") or "",
            }
            d = create_document(section_text, md, doc_id=doc_id)
            # If a section is too large (common for PDFs without headings), split it further.
            section_parts = self._split_if_oversized(d, chunk_id_prefix=f"{doc_id}_section_{i}")
            for j, part in enumerate(section_parts):
                part.metadata["chunk_index"] = j
                part.metadata["chunk_id"] = f"{doc_id}_section_{i}_{j}"
                all_chunks.append(part)

        # 2) Paragraphs (bounded)
        paragraphs = self._split_into_paragraphs(text)
        para_kept = 0
        for i, p in enumerate(paragraphs):
            if para_kept >= self.max_paragraph_chunks:
                break
            p = p.strip()
            if len(p) < self.min_paragraph_chars:
                continue
            md = {
                **metadata,
                "chunk_type": "paragraph",
                "paragraph_index": para_kept,
            }
            d = create_document(p, md, doc_id=doc_id)
            para_parts = self._split_if_oversized(d, chunk_id_prefix=f"{doc_id}_paragraph_{para_kept}")
            for j, part in enumerate(para_parts):
                part.metadata["chunk_index"] = j
                part.metadata["chunk_id"] = f"{doc_id}_paragraph_{para_kept}_{j}"
                all_chunks.append(part)
            para_kept += 1

        # 3) Semantic overlap chunks (best default)
        semantic_chunks = self.chunk_text(text, {**metadata, "chunk_type": "semantic"}, doc_id=doc_id)
        for i, ch in enumerate(semantic_chunks):
            ch.metadata["chunk_type"] = "semantic"
            ch.metadata["chunk_index"] = i
            ch.metadata["chunk_id"] = f"{doc_id}_semantic_{i}"
        all_chunks.extend(semantic_chunks)

        return all_chunks

    def _split_if_oversized(self, doc: Document, chunk_id_prefix: str) -> list[Document]:
        """Split a Document further if its text is too large."""
        content = (doc.page_content or "")
        if len(content) <= self.max_chunk_chars:
            return [doc]

        # Reuse the recursive splitter but with a larger chunk size than the semantic chunks.
        # This keeps section/paragraph chunks meaningful while staying under embedding limits.
        splitter = get_recursive_splitter(
            chunk_size=min(max(self.chunk_size * 2, 1500), 3000),
            chunk_overlap=min(self.chunk_overlap, 200),
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        parts = split_documents([doc], splitter)
        for k, p in enumerate(parts):
            p.metadata["chunk_id"] = f"{chunk_id_prefix}_{k}"
        return parts

    def _split_into_paragraphs(self, text: str) -> list[str]:
        # Prefer blank lines; fallback to sentence-ish splits if the doc is a wall of text.
        if "\n\n" in text:
            parts = [p for p in text.split("\n\n") if p.strip()]
        else:
            # Split on strong punctuation boundaries.
            parts = re.split(r"(?<=[.!?])\s{2,}", text)
        return parts

    def _split_into_sections(self, text: str) -> list[dict[str, str]]:
        """Heuristic section splitter.

        Handles:
          - Markdown headings (#, ##, ...)
          - Numbered headings (e.g. '1. Introduction', '2.3 Pest control')
          - ALL CAPS headings (common in PDFs)
        """

        lines = text.split("\n")
        headings: list[tuple[int, str]] = []

        heading_re = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
        numbered_re = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\.?\s+(.+?)\s*$")

        for idx, raw in enumerate(lines):
            line = raw.strip()
            if not line:
                continue

            m = heading_re.match(line)
            if m:
                headings.append((idx, m.group(2)))
                continue

            m = numbered_re.match(line)
            if m and len(line) <= 120:
                headings.append((idx, f"{m.group(1)} {m.group(2)}"))
                continue

            if line.isupper() and 4 <= len(line) <= 80:
                headings.append((idx, line.title()))

        if not headings:
            return [{"title": "", "content": text}]

        sections: list[dict[str, str]] = []
        for i, (start_idx, title) in enumerate(headings):
            end_idx = headings[i + 1][0] if i + 1 < len(headings) else len(lines)
            content = "\n".join(lines[start_idx:end_idx]).strip()
            if content:
                sections.append({"title": title, "content": content})

        return sections

    def chunk_multiple(
        self,
        texts: list[tuple[str, dict]],
    ) -> list[Document]:
        all_chunks = []
        for text, metadata in texts:
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        return all_chunks