FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Copy requirements inferred from project (minimal)
COPY *.py readme.md index.html /app/

# Ensure data dir exists for SQLite
RUN mkdir -p /app/data

# Install dependencies (FastAPI, uvicorn, sqlmodel, crawl4ai, playwright already present)
RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlmodel sqlalchemy crawl4ai bs4

# Expose port
EXPOSE 8000

# Command to run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
