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
