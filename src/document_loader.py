"""
Loads TXT and PDF files from the /data directory.
"""

import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader


def load_documents(data_dir: str) -> list:
    """
    Load all .txt and .pdf documents from the given directory.
    Returns a list of LangChain Document objects.
    """
    documents = []
    supported_extensions = (".txt", ".pdf")

    for filename in os.listdir(data_dir):
        if not filename.lower().endswith(supported_extensions):
            continue

        filepath = os.path.join(data_dir, filename)

        try:
            if filename.lower().endswith(".pdf"):
                loader = PyPDFLoader(filepath)
            else:
                loader = TextLoader(filepath, encoding="utf-8")

            docs = loader.load()
            # Tag each doc with source filename
            for doc in docs:
                doc.metadata["source"] = filename
            documents.extend(docs)
            print(f"  [OK] Loaded: {filename} ({len(docs)} page(s))")

        except Exception as e:
            print(f"  [WARN] Could not load {filename}: {e}")

    print(f"\n  Total documents loaded: {len(documents)}")
    return documents


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_folder = os.path.join(base_dir, "data")
    docs = load_documents(data_folder)
    print(f"Sample content preview:\n{docs[0].page_content[:300]}")
