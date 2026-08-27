FROM node:22.14.0-alpine3.21 AS frontend-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13.2-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 FORWARDED_ALLOW_IPS=127.0.0.1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
 && addgroup --system stockflow && adduser --system --ingroup stockflow stockflow
COPY --chown=stockflow:stockflow backend/ ./
COPY --from=frontend-build --chown=stockflow:stockflow /build/frontend/dist ./app/static
USER stockflow
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
