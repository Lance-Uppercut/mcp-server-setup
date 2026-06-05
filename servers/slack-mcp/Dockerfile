FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "mcp[cli]>=1.27.2" \
    httpx

COPY server.py .

ENV SLACK_BOT_TOKEN=
ENV SLACK_DEFAULT_REPLY_TIMEOUT_SECONDS=300
ENV SLACK_REPLY_POLL_INTERVAL_SECONDS=5
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=3108

EXPOSE 3108

CMD ["python", "server.py"]
