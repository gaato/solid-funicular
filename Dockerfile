FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir py-cord python-dotenv

COPY src ./src
COPY data/.gitignore ./data/.gitignore
RUN mkdir -p /app/data \
    && printf '{}' > /app/data/users.json \
    && printf '{}' > /app/data/punishment.json

CMD ["python", "-m", "solid_funicular.main"]
