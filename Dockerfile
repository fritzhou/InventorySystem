FROM node:22-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 stockflow
COPY --chown=stockflow:stockflow backend/ ./
COPY --from=frontend-build --chown=stockflow:stockflow /build/frontend/dist ./static
USER stockflow
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --forwarded-allow-ips ${PROXY_FORWARDED_ALLOW_IPS:-127.0.0.1}"]
