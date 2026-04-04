# Avigilance 2.0 — India Aviation Safety Monitoring OpenEnv
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

WORKDIR $APP_HOME

# Use pre-built wheels only — avoids compilation OOM on HF free tier
COPY requirements-space.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements-space.txt \
    || pip install --no-cache-dir -r requirements-space.txt

COPY . .

RUN mkdir -p data

# Run as non-root user (required for HuggingFace Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH

# Pre-generate synthetic data at build time
RUN python3 generate_data.py

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
