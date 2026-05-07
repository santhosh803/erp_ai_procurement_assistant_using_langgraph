"""
Splits loaded documents into smaller overlapping chunks for embedding.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(documents: list, chunk_size: int = 500, chunk_overlap: int = 50) -> list:
    """
    Split a list of LangChain Document objects into smaller text chunks.

    Args:
        documents: List of Document objects from document_loader.
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        List of chunked Document objects.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    chunks = splitter.split_documents(documents)
    print(f"  Total chunks created: {len(chunks)}")
    return chunks


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.document_loader import load_documents

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_folder = os.path.join(base_dir, "data")

    docs = load_documents(data_folder)
    chunks = chunk_documents(docs)
    print(f"\nSample chunk:\n{chunks[0].page_content}")
    print(f"Source: {chunks[0].metadata.get('source', 'unknown')}")
