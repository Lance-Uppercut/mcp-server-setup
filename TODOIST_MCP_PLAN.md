# Todoist MCP Server Implementation Plan

## Goal
Add Todoist MCP server to the mcp-server-setup stack, building and deploying via Jenkins pipeline.

## Steps

### 1. Create server directory and files
- `servers/todoist-mcp/Dockerfile` - Python-based container
- `servers/todoist-mcp/requirements.txt` - Dependencies
- `servers/todoist-mcp/server.py` - Main entry point using todoist-mcp-server

### 2. Update docker-compose.yml
- Add todoist-mcp service with build context
- Use registry image (registry:5000/offbeat-iot/todoist-mcp:latest) after first build

### 3. Update Jenkinsfile
- Add to services list: `[imageName: 'todoist-mcp', context: './servers/todoist-mcp']`
- Build and push with other services

### 4. Test in Jenkins pipeline
- Verify build succeeds
- Verify deploy stage runs without hanging
- Verify container starts and connects to Todoist API

## Configuration
- API Token: Provided by user (stored in Jenkins credentials)
- Port: 3104
- Image: registry:5000/offbeat-iot/todoist-mcp:latest