# =============================================================================
# Dockerfile — Container Image for the API
# =============================================================================
# Railway does NOT use this file (it uses Nixpacks to auto-build).
# This Dockerfile is only for local Docker Compose development.
# =============================================================================

FROM python:3.12-slim

# Set the working directory inside the container.
WORKDIR /app

# Install dependencies first (cached if requirements.txt hasn't changed).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .

# Default command (overridden by docker-compose.yml).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
