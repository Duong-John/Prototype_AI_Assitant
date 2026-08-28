# Use official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Command to run the application using Uvicorn
# Note: Render provides a $PORT environment variable, but we can default to 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]