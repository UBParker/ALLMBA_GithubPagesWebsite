FROM python:3.9-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m nltk.downloader punkt stopwords wordnet

# Copy the application code
COPY . .

# Make sure data directories exist
RUN mkdir -p data/raw
RUN mkdir -p data/processed

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the FastAPI application with uvicorn
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8080"]