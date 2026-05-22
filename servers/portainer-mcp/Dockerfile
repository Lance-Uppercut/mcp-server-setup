FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    mcp[cli] \
    httpx

COPY server.py .

ENV PORTAINER_BASE_URL=http://localhost:6500
ENV PORTAINER_TOKEN=
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=3111

EXPOSE 3111

CMD ["python", "server.py"]
