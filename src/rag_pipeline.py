"""
Wires together: Retriever → Prompt Builder → LLM Handler.
This is the core RAG query pipeline.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retriever import Retriever
from src.prompt_builder import build_prompt
from src.llm_handler import generate_response


class RAGPipeline:
    def __init__(self, top_k: int = 4):
        """
        Args:
            top_k: Number of document chunks to retrieve per query.
        """
        self.retriever = Retriever(k=top_k)

    def ask(self, query: str) -> dict:
        """
        Run the full RAG pipeline for a user query.

        Args:
            query: Natural language question from the user.

        Returns:
            Dict with:
                'answer'  — LLM-generated response
                'sources' — list of source filenames used
                'chunks'  — list of retrieved chunks (content + source)
        """
        # Step 1: Retrieve relevant chunks
        chunks = self.retriever.retrieve(query)

        # Step 2: Build the prompt
        prompt = build_prompt(query, chunks)

        # Step 3: Generate response via LLM
        answer = generate_response(prompt)

        # Collect unique source filenames
        sources = list({chunk["source"] for chunk in chunks})

        return {
            "answer": answer,
            "sources": sources,
            "chunks": chunks,
        }


if __name__ == "__main__":
    print("ERP AI Procurement Assistant — Interactive Test")
    print("Type 'exit' to quit.\n")

    pipeline = RAGPipeline(top_k=4)

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit", "q"):
            break
        if not user_input:
            continue

        result = pipeline.ask(user_input)
        print(f"\nAssistant: {result['answer']}")
        print(f"\nSources: {', '.join(result['sources'])}")
        print("-" * 60)
