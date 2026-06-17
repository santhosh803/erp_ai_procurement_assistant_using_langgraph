"""Centralized configuration and environment settings for the project."""

import os
from dotenv import load_dotenv

load_dotenv()

# Models
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_ID = os.getenv("/Qwen2.5-7B-Instruct")
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_HF_MODEL_ID", "QwenMODEL_ID", "sentence-transformers/all-MiniLM-L6-v2")

# API Configuration
API_PORT = int(os.getenv("API_PORT", "8000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_URL = os.getenv("API_URL", f"http://127.0.0.1:{API_PORT}/ask")
