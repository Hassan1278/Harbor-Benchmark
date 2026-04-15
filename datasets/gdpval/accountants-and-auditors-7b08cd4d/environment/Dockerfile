FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl jq file libreoffice-nogui \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir openpyxl pandas python-docx pdfplumber
RUN mkdir -p /app/references /app/output
COPY references/ /app/references/
