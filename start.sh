#!/bin/bash

# Start the FastAPI backend in the background (bind to 0.0.0.0 for reliability in Docker)
echo "Starting FastAPI backend on port 8000..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Wait for a few seconds to ensure the API starts up
sleep 3

# Start the Streamlit frontend in the foreground on port 7860
# Port 7860 is the port that Hugging Face Spaces exposes
echo "Starting Streamlit frontend on port 7860..."
python -m streamlit run ui/app.py --server.port 7860 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
