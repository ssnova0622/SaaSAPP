# Backend API for SaaS project
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY settings.py .
COPY app/ ./app/

# Default: run uvicorn with factory (create_app)
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host $HOST --port $PORT"]
