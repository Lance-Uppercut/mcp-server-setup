# Slack MCP Server

Custom Slack MCP server for Sentinel workflows.

## Tools

- `slack_create_channel`
- `slack_post_message_and_wait_for_reply`
- `slack_post_message_to_thread`

## Required configuration

- `SLACK_BOT_TOKEN`: Slack bot token with the scopes needed for channel creation, posting messages, and reading thread replies.

## Optional configuration

- `SLACK_DEFAULT_REPLY_TIMEOUT_SECONDS`: Default wait timeout for `slack_post_message_and_wait_for_reply`. Default: `300`.
- `SLACK_REPLY_POLL_INTERVAL_SECONDS`: Poll interval while waiting for replies. Default: `5`.
- `MCP_HOST`: Bind host. Default: `0.0.0.0`.
- `MCP_PORT`: Bind port. Default: `3108`.
