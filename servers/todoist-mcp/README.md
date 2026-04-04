# Todoist MCP Server

MCP server for Todoist task management using the [todoist-mcp-server](https://github.com/mikemc/todoist-mcp-server) Python package.

## Library

This server uses [mikemc/todoist-mcp-server](https://github.com/mikemc/todoist-mcp-server) (MIT license) which wraps the official [Todoist REST API](https://developer.todoist.com/rest/v2/).

## Configuration

Configure via environment variables:

| Variable | Description |
|----------|-------------|
| `TODOIST_API_TOKEN` | Your Todoist API token |
| `MCP_HOST` | Server host (default: 0.0.0.0) |
| `MCP_PORT` | Server port (default: 3104) |

### Getting API Token

1. Log in to [Todoist](https://todoist.com)
2. Go to Settings → Integrations
3. Find your API token under "Developer"

## Available Tools

### Projects
- `todoist_get_projects` - Get all projects
- `todoist_get_project` - Get specific project
- `todoist_add_project` - Create new project
- `todoist_update_project` - Update project
- `todoist_delete_project` - Delete project

### Sections
- `todoist_get_sections` - Get sections in a project
- `todoist_add_section` - Create section
- `todoist_update_section` - Update section
- `todoist_delete_section` - Delete section

### Tasks
- `todoist_get_tasks` - Get tasks
- `todoist_filter_tasks` - Filter tasks
- `todoist_add_task` - Create task
- `todoist_update_task` - Update task
- `todoist_complete_task` - Complete task
- `todoist_uncomplete_task` - Uncomplete task
- `todoist_delete_task` - Delete task

### Comments
- `todoist_get_comments` - Get comments on task
- `todoist_add_comment` - Add comment to task