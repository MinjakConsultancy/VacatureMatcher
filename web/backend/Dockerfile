FROM python:3.13-slim-bookworm

WORKDIR /app

COPY web/backend/requirements.txt /tmp/backend-req.txt
COPY rag/requirements.txt /tmp/rag-req.txt
COPY db/requirements.txt /tmp/db-req.txt

RUN pip install --no-cache-dir -r /tmp/backend-req.txt -r /tmp/rag-req.txt -r /tmp/db-req.txt

COPY db /app/db
COPY rag /app/rag
COPY web/backend/app /app/app

ENV PYTHONPATH=/app:/app/db:/app/rag
ENV RAG_INDEX_DIR=/data/rag-index

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
