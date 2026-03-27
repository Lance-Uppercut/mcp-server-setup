FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git curl jq wget docker.io nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://github.com/anomalyco/opencode/releases/download/v1.3.2/opencode-linux-x64.tar.gz -o /tmp/opencode.tar.gz \
    && tar -xzf /tmp/opencode.tar.gz -C /usr/local/bin \
    && rm /tmp/opencode.tar.gz \
    && chmod +x /usr/local/bin/opencode

RUN pip install --no-cache-dir mcp

RUN npm install -g @openai/codex

WORKDIR /app

# Mount docker-compose at runtime via docker-compose.yml
# MCP config is at /root/.config/opencode/opencode.json

ENTRYPOINT ["opencode"]
