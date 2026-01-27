# Use the official slim version of Python to reduce image size
FROM python:3.11.5-slim

# Set the working directory inside the container
WORKDIR /code

# Install system dependencies required for FastAPI and Uvicorn
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker caching
COPY requirements.txt .

# Upgrade pip and install dependencies without cache to reduce image size
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose FastAPI's default port
EXPOSE 8000

# Command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "fastapi_app:app1", "--host", "0.0.0.0", "--port", "8000"]
