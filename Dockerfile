# Stage 1: Build admin UI (React / Vite)
FROM node:20-alpine AS ui-build
WORKDIR /ui
COPY admin_ui/package.json admin_ui/package-lock.json ./
RUN npm ci
COPY admin_ui/ ./
# Same-origin API when served from FastAPI
ENV VITE_API_BASE=/v1
RUN npm run build

# Stage 2: API + static admin UI
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY settings.py .
COPY app/ ./app/
COPY --from=ui-build /ui/dist ./static/admin

ENV HOST=0.0.0.0
ENV PORT=8000
ENV SERVE_ADMIN_UI=true
ENV RELOAD=false
ENV DEBUG=false

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host $HOST --port $PORT"]
