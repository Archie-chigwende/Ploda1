FROM python:3.12-slim AS document-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY requirements-docs.txt generate_documents.py /build/
RUN pip install --no-cache-dir -r requirements-docs.txt \
    && python3 generate_documents.py

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLODA_ENV=production \
    HOST=0.0.0.0 \
    PORT=8080 \
    PLODA_DB_PATH=/data/ploda.db

WORKDIR /app
COPY app.py /app/app.py
COPY static /app/static
COPY --from=document-builder /build/documents /app/documents
RUN mkdir -p /data && useradd --create-home --uid 10001 ploda && chown -R ploda:ploda /app /data
USER ploda

EXPOSE 8080
CMD ["python3", "app.py"]
