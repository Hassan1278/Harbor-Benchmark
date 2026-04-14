FROM python:3.11-slim

WORKDIR /app

# Install common tools for document handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    openpyxl \
    pandas \
    python-docx \
    pdfplumber \
    requests

# Reference files will be downloaded at runtime by the agent
# or pre-loaded by the adapter
