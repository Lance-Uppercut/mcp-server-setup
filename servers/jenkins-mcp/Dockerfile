FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    mcp[cli] \
    httpx

COPY server.py .

ENV JENKINS_URL=http://localhost:8080
ENV JENKINS_USERNAME=
ENV JENKINS_API_TOKEN=
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=3117

EXPOSE 3117

CMD ["python", "server.py"]
