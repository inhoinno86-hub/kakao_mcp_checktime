FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    CHECKTIME_MCP_DATA_DIR=/app/data

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY data /app/data

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "checktime_mcp.mcp_server", "--transport", "http", "--host", "0.0.0.0"]
