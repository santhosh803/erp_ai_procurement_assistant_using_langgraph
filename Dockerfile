# Use official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install dependencies, including system packages needed for some python libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 7860 to the outside world (Hugging Face Spaces requirement)
EXPOSE 7860
# Port 8000 is used internally by FastAPI
EXPOSE 8000

# Ensure the script has unix line endings and execution permission
RUN dos2unix start.sh && chmod +x start.sh

# Start both FastAPI and Streamlit using the shell script
CMD ["./start.sh"]
