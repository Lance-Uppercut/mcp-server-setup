FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    mcp[cli] \
    httpx

COPY server.py .

ENV ALERTMANAGER_URL=
ENV ALERTMANAGER_USERNAME=
ENV ALERTMANAGER_PASSWORD=
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python3 -c "import sys,urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8001/sse', timeout=2); sys.exit(0 if r.status == 200 else 1)"

CMD ["python", "server.py"]
