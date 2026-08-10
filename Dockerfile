FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential curl libsndfile1 ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install "."

COPY alembic.ini ./
COPY migrations ./migrations
COPY static ./static
COPY scripts ./scripts

EXPOSE 8088
CMD ["uvicorn", "betman_voice.main:app", "--host", "0.0.0.0", "--port", "8088", "--proxy-headers"]
