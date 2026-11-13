FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY pyproject.toml README.md LICENSE ./
COPY voice_ai_lab ./voice_ai_lab
RUN pip install --no-cache-dir --no-deps . && useradd -u 10001 -m lab \
    && mkdir -p /app/.local && chown -R lab:lab /app/.local
USER lab
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "voice_ai_lab.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]

FROM app AS tests
USER root
COPY requirements-dev.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements-dev.lock
COPY tests ./tests
COPY scripts ./scripts
COPY evals ./evals
USER lab
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
