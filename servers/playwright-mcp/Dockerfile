FROM mcr.microsoft.com/playwright/mcp:latest

ENV PLAYWRIGHT_MCP_HOST=0.0.0.0
ENV PLAYWRIGHT_MCP_PORT=3106
ENV PLAYWRIGHT_MCP_HEADLESS=true
ENV PLAYWRIGHT_MCP_NO_SANDBOX=true

EXPOSE 3106

ENTRYPOINT ["node", "cli.js", "--port", "3106", "--host", "0.0.0.0", "--headless", "--no-sandbox"]