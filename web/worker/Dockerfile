FROM python:3.13-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    libpango-1.0-0 libcairo2 libatspi2.0-0 \
    nodejs npm xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY web/backend/requirements.txt /tmp/backend-req.txt
COPY rag/requirements.txt /tmp/rag-req.txt
COPY db/requirements.txt /tmp/db-req.txt

RUN pip install --no-cache-dir -r /tmp/backend-req.txt -r /tmp/rag-req.txt -r /tmp/db-req.txt

COPY . /app
COPY web/backend/app /app/app

# Node Playwright voor run_ververs.sh (IkWerk-browserfetch)
RUN cd /app/scraper \
    && npm install playwright@^1.61.0 --no-save \
    && node node_modules/playwright/cli.js install chromium

ENV PYTHONPATH=/app:/app/db:/app/rag
ENV RAG_INDEX_DIR=/data/rag-index
ENV NODE_PATH=/app/scraper/node_modules

CMD ["python", "/app/web/worker/worker.py"]
