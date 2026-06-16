# AGENTS

## Credential Propagation

When a service in `docker-stack.yml` needs a secret at deploy time:

1. Add the Jenkins credential to the `withCredentials([...])` block in `Jenkinsfile`.
2. Map that bound value into the deploy environment with `withEnv([...])`.
3. Reference the environment variable from `docker-stack.yml` using `${VAR_NAME:-}`.

Example used for Slack:

- Jenkins credential ID: `slack-bot-token`
- Jenkins variable: `MCP_SLACK_BOT_TOKEN`
- Deploy environment variable: `SLACK_BOT_TOKEN`
- Stack reference: `SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN:-}`

This keeps secrets in Jenkins while still allowing `docker stack deploy` to substitute the values into the stack environment.

## Headroom Proxy Usage

The `headroom-proxy` service at `http://headroom-proxy:8787/v1` compresses LLM context before it reaches the upstream provider (60-95% fewer tokens).

- **Point any OpenAI-compatible client** at `http://headroom-proxy:8787/v1` as the base URL.
- **Claude Code** inside the opencode container: `headroom wrap claude` or set `ANTHROPIC_BASE_URL=http://headroom-proxy:8787/v1`.
- **MCP tools** (`headroom_compress`, `headroom_retrieve`, `headroom_stats`) are available by running `headroom mcp install` inside a client container.
- **Upstream** defaults to OpenAI. Override via `OPENAI_TARGET_API_URL` or `HEADROOM_TARGET_API_URL` env var for Anthropic, xAI, Ollama, etc.
