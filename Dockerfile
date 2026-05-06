FROM python:3.9-slim
LABEL maintainer="Sobevita Team"
LABEL description="Sobevita Automation - Content & Product Management API"
LABEL version="1.0.0"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libssl-dev libffi-dev python3-dev curl wget git && rm -rf /var/lib/apt/lists/* && apt-get clean
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
COPY . .
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "gevent", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "app:app"]
