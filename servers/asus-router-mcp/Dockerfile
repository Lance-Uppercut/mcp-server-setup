FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    mcp[cli] \
    asusrouter \
    httpx \
    uvicorn \
    starlette \
    anyio

COPY server.py .

ENV TRANSPORT_MODE=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=3105

EXPOSE 3105

CMD ["python", "server.py"]