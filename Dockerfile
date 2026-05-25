# Use official Python runtime as a parent image
FROM python:3.9-slim

# Install dependencies, including system packages needed for some python libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python requirements globally
RUN pip install --no-cache-dir -r requirements.txt

# Set up a new user named "user" with UID 1000
RUN useradd -m -u 1000 user

# Set the home and working directory
ENV HOME=/home/user
WORKDIR $HOME/app

# Copy the rest of the application setting the owner to user 1000
COPY --chown=user . .

# Ensure the script has unix line endings and execution permission
# Run this as root before switching user
RUN dos2unix start.sh && chmod +x start.sh

# Switch to the "user" user
USER user

# Pre-download the sentence-transformers model to the user's cache
RUN python -c "from src.config import EMBEDDING_MODEL_ID; from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_ID)"

# Build the FAISS index during the image build to ensure it's up-to-date
RUN python src/ingest_pipeline.py

# Expose port 7860 to the outside world (Hugging Face Spaces requirement)
EXPOSE 7860
# Port 8000 is used internally by FastAPI
EXPOSE 8000

# Start both FastAPI and Streamlit using the shell script
CMD ["./start.sh"]
