# ─── Frontend build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --omit=dev
COPY frontend/ .
RUN npm run build

# ─── Backend ────────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything except data dir
COPY --from=frontend /frontend/out /app/frontend/out
COPY . .



EXPOSE 8000

VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import http.client; c=http.client.HTTPConnection('localhost',8000); c.request('GET','/api/v1/stats'); r=c.getresponse(); exit(0 if r.status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
