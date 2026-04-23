@Library("shared-jenkins-pipelines") _

def quoteEnvValue(String value) {
    '"' + (value ?: '')
        .replace('\\', '\\\\')
        .replace('"', '\\"')
        .replace('$', '$$') + '"'
}

pipeline {
    agent {
        label 'build1'
    }
    
    options {
        requiresBuildSlot true
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }
    
    environment {
        DOCKER_REGISTRY = 'registry:5000'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build and Push Docker images') {
            steps {
                script {
                    def branchName = env.BRANCH_NAME ?: env.GIT_BRANCH ?: env.CHANGE_BRANCH
                    def sanitizedBranch = io.jenkins.pipeline.TagUtils.sanitizeTag(branchName ?: 'main')

                    def shortSha = sh(script: 'git rev-parse --short=5 HEAD', returnStdout: true).trim()
                    
                    echo "Building branch: ${sanitizedBranch}, SHA: ${shortSha}"
                    
                    def services = [
                        [imageName: 'google-workspace-mcp', context: './servers/mcp-google-workspace'],
                        [imageName: 'yahoo-mail-mcp-server', context: './servers/yahoo-mail-mcp-server'],
                        [imageName: 'tado-mcp', context: './servers/tado-mcp'],
                        [imageName: 'asus-router-mcp', context: './servers/asus-router-mcp']
                    ]
                    
                    echo "Services to build: ${services.collect { it.imageName }.join(', ')}"
                    
                    for (int i = 0; i < services.size(); i++) {
                        def service = services[i]
                        def currentImageName = service.imageName
                        def currentContext = service.context
                        echo "Building service ${i+1}/${services.size()}: ${currentImageName} with branch name: ${sanitizedBranch}"
                        dir(currentContext) {
                            buildAndPushImage(
                                artifactId: currentImageName,
                                branchName: sanitizedBranch,
                                gitHash: shortSha
                            )
                        }
                    }
                }
            }
        }
        
        stage('Deploy') {

            steps {
                script {
                    echo "Deploying MCP servers..."
                    def mcpDataDir = '/home/jenkins/mcp-server-setup-data'

                    def runtimeEnvSpecs = [
                        [envName: 'ANTHROPIC_API_KEY', credentialId: 'mcp-anthropic-api-key', variable: 'SECRET_ANTHROPIC_API_KEY'],
                        [envName: 'GITHUB_TOKEN', credentialId: 'mcp-github-token', variable: 'SECRET_GITHUB_TOKEN'],
                        [envName: 'GOOGLE_CLIENT_ID', credentialId: 'mcp-google-client-id', variable: 'SECRET_GOOGLE_CLIENT_ID'],
                        [envName: 'GOOGLE_CLIENT_SECRET', credentialId: 'mcp-google-client-secret', variable: 'SECRET_GOOGLE_CLIENT_SECRET'],
                        [envName: 'JENKINS_URL', credentialId: 'mcp-jenkins-url', variable: 'SECRET_JENKINS_URL'],
                        [envName: 'JENKINS_USERNAME', credentialId: 'mcp-jenkins-username', variable: 'SECRET_JENKINS_USERNAME'],
                        [envName: 'JENKINS_API_TOKEN', credentialId: 'mcp-jenkins-api-token', variable: 'SECRET_JENKINS_API_TOKEN'],
                        [envName: 'TODOIST_API_TOKEN', credentialId: 'mcp-todoist-api-token', variable: 'SECRET_TODOIST_API_TOKEN'],
                        [envName: 'YAHOO_EMAIL', credentialId: 'mcp-yahoo-email', variable: 'SECRET_YAHOO_EMAIL'],
                        [envName: 'YAHOO_APP_PASSWORD', credentialId: 'mcp-yahoo-app-password', variable: 'SECRET_YAHOO_APP_PASSWORD'],
                        [envName: 'ALERTMANAGER_URL', credentialId: 'mcp-alertmanager-url', variable: 'SECRET_ALERTMANAGER_URL'],
                        [envName: 'ROUTER_PASSWORD', credentialId: 'mcp-router-password', variable: 'SECRET_ROUTER_PASSWORD'],
                        [envName: 'PORTAINER_BUILD1_TOKEN', credentialId: 'mcp-portainer-build1-token', variable: 'SECRET_PORTAINER_BUILD1_TOKEN'],
                        [envName: 'PORTAINER_BUILD2_TOKEN', credentialId: 'mcp-portainer-build2-token', variable: 'SECRET_PORTAINER_BUILD2_TOKEN'],
                        [envName: 'PORTAINER_MONITOR_TOKEN', credentialId: 'mcp-portainer-monitor-token', variable: 'SECRET_PORTAINER_MONITOR_TOKEN'],
                        [envName: 'PORTAINER_OBSERVABILITY1_TOKEN', credentialId: 'mcp-portainer-observability1-token', variable: 'SECRET_PORTAINER_OBSERVABILITY1_TOKEN'],
                        [envName: 'PORTAINER_TOOLS1_TOKEN', credentialId: 'mcp-portainer-tools1-token', variable: 'SECRET_PORTAINER_TOOLS1_TOKEN'],
                        [envName: 'PORTAINER_PRODUCTION1_TOKEN', credentialId: 'mcp-portainer-production1-token', variable: 'SECRET_PORTAINER_PRODUCTION1_TOKEN']
                    ]

                    def runtimeFileSpecs = [
                        [credentialId: 'mcp-google-gauth-json', variable: 'SECRET_GOOGLE_GAUTH_FILE'],
                        [credentialId: 'mcp-google-accounts-json', variable: 'SECRET_GOOGLE_ACCOUNTS_FILE'],
                        [credentialId: 'mcp-google-oauth2-seed-json', variable: 'SECRET_GOOGLE_OAUTH2_SEED_FILE'],
                        [credentialId: 'mcp-tado-tokens-json', variable: 'SECRET_TADO_TOKENS_FILE']
                    ]

                    def credentialBindings = runtimeEnvSpecs.collect { spec ->
                        string(credentialsId: spec.credentialId, variable: spec.variable)
                    } + runtimeFileSpecs.collect { spec ->
                        file(credentialsId: spec.credentialId, variable: spec.variable)
                    }

                    withCredentials(credentialBindings) {
                        sh '''
                            mkdir -p ./runtime-secrets
                            chmod 700 ./runtime-secrets
                        '''

                        def runtimeEnvContent = runtimeEnvSpecs.collect { spec ->
                            "${spec.envName}=${quoteEnvValue(env."${spec.variable}")}"
                        }
                        runtimeEnvContent += "MCP_DATA_DIR=${quoteEnvValue(mcpDataDir)}"
                        runtimeEnvContent += "COMPOSE_PROJECT_NAME=${quoteEnvValue('mcp-servers')}"
                        runtimeEnvContent = runtimeEnvContent.join('\n') + '\n'

                        writeFile(file: './runtime-secrets/runtime.env', text: runtimeEnvContent)
                        sh 'chmod 600 ./runtime-secrets/runtime.env'

                        def gatewaySecretsContent = [
                            "github.personal_access_token=${quoteEnvValue(env.SECRET_GITHUB_TOKEN)}",
                            "portainer_build1.token=${quoteEnvValue(env.SECRET_PORTAINER_BUILD1_TOKEN)}",
                            "portainer_build2.token=${quoteEnvValue(env.SECRET_PORTAINER_BUILD2_TOKEN)}",
                            "portainer_monitor.token=${quoteEnvValue(env.SECRET_PORTAINER_MONITOR_TOKEN)}",
                            "portainer_observability1.token=${quoteEnvValue(env.SECRET_PORTAINER_OBSERVABILITY1_TOKEN)}",
                            "portainer_tools1.token=${quoteEnvValue(env.SECRET_PORTAINER_TOOLS1_TOKEN)}",
                            "portainer_production1.token=${quoteEnvValue(env.SECRET_PORTAINER_PRODUCTION1_TOKEN)}"
                        ].join('\n') + '\n'
                        writeFile(file: './runtime-secrets/gateway-secrets.env', text: gatewaySecretsContent)
                        sh 'chmod 600 ./runtime-secrets/gateway-secrets.env'

                        sh '''
                            python3 - <<'PY'
import json
import os
from pathlib import Path

seed_path = os.environ.get("SECRET_GOOGLE_OAUTH2_SEED_FILE")
if not seed_path or not os.path.exists(seed_path):
    raise SystemExit(0)

raw = Path(seed_path).read_text().strip()
if not raw:
    raise SystemExit(0)

try:
    parsed = json.loads(raw)
except Exception as exc:
    raise SystemExit(f"Invalid mcp-google-oauth2-seed-json content: {exc}")

if not isinstance(parsed, dict):
    raise SystemExit("Credential mcp-google-oauth2-seed-json must be a JSON object keyed by .oauth2.*.json filenames.")

base = Path("./runtime-secrets/google-oauth2-seed")
base.mkdir(parents=True, exist_ok=True)

for filename, payload in parsed.items():
    if not isinstance(filename, str) or not filename.startswith(".oauth2.") or not filename.endswith(".json"):
        raise SystemExit(f"Invalid Google OAuth seed filename: {filename}")
    target = base / filename
    if target.exists():
        continue
    rendered = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    if not rendered.endswith("\\n"):
        rendered += "\\n"
    target.write_text(rendered)
    print(f"Prepared Google OAuth seed file at {target}")
PY
                        '''

                        def composeCommand = 'docker compose --env-file ./runtime-secrets/runtime.env'

                        sh script: "${composeCommand} down --remove-orphans", returnStatus: true

                        timeout(time: 5, unit: 'MINUTES') {
                            sh "${composeCommand} pull"
                            sh "${composeCommand} up -d"
                        }

                        sh """
                            mcpGatewayContainer=\$(${composeCommand} ps -q mcp-gateway)
                            echo "MCP Gateway container: \$mcpGatewayContainer"
                            if [ -n "\$mcpGatewayContainer" ]; then
                                sleep 10
                                echo "MCP Gateway startup logs (tail 120):"
                                docker logs "\$mcpGatewayContainer" --tail 120 || true
                            fi
                            googleContainer=\$(${composeCommand} ps -q google-workspace-mcp)
                            tadoContainer=\$(${composeCommand} ps -q tado-mcp)

                            if [ -z "\$googleContainer" ]; then
                                echo "google-workspace-mcp container not found"
                                exit 1
                            fi
                            if [ -z "\$tadoContainer" ]; then
                                echo "tado-mcp container not found"
                                exit 1
                            fi

                            docker cp "\$SECRET_GOOGLE_GAUTH_FILE" "\$googleContainer:/data/google-workspace/.gauth.json"
                            docker cp "\$SECRET_GOOGLE_ACCOUNTS_FILE" "\$googleContainer:/data/google-workspace/.accounts.json"
                            docker exec "\$googleContainer" sh -lc 'mkdir -p /data/google-workspace/credentials && chmod 600 /data/google-workspace/.gauth.json /data/google-workspace/.accounts.json'

                            if [ -d ./runtime-secrets/google-oauth2-seed ]; then
                                for seedFile in ./runtime-secrets/google-oauth2-seed/.oauth2.*.json; do
                                    [ -f "\$seedFile" ] || continue
                                    seedName=\$(basename "\$seedFile")
                                    if ! docker exec "\$googleContainer" test -f "/data/google-workspace/credentials/\$seedName"; then
                                        docker cp "\$seedFile" "\$googleContainer:/data/google-workspace/credentials/\$seedName"
                                        docker exec "\$googleContainer" chmod 600 "/data/google-workspace/credentials/\$seedName"
                                    fi
                                done
                            fi

                            docker cp "\$SECRET_TADO_TOKENS_FILE" "\$tadoContainer:/data/tokens.json"
                            docker exec "\$tadoContainer" chmod 600 /data/tokens.json

                            ${composeCommand} restart google-workspace-mcp tado-mcp

                            node ./scripts/activate-gateway-servers.js "http://localhost:3100/sse" "github,playwright,jenkins,portainer_build1,portainer_build2,portainer_monitor,portainer_observability1,portainer_tools1,portainer_production1"

                            echo "Gateway catalog probe for portainer:" 
                            npx -y @modelcontextprotocol/inspector --cli "http://localhost:3100/sse" --transport sse --method tools/call --tool-name mcp-find --tool-arg query=portainer || true
                            echo "Gateway catalog probe for jenkins:" 
                            npx -y @modelcontextprotocol/inspector --cli "http://localhost:3100/sse" --transport sse --method tools/call --tool-name mcp-find --tool-arg query=jenkins || true
                            echo "Gateway mounted custom-catalog.yaml (first 140 lines):"
                            docker exec "\$mcpGatewayContainer" sh -lc 'awk "NR<=140{print}" /gateway/custom-catalog.yaml' || true

                            echo "MCP Gateway logs after activation (tail 200):"
                            docker logs "\$mcpGatewayContainer" --tail 200 || true
                        """

                        sh "${composeCommand} ps"

                        echo "Deployment complete!"
                    }
                }
            }
        }

        stage('Verify MCP servers') {
            steps {
                script {
                    sh 'chmod +x ./scripts/verify-mcp-servers.sh'
                    sh './scripts/verify-mcp-servers.sh --host localhost'
                }
            }
        }

        stage('Verify in OpenCode container') {
            steps {
                script {
                    def composeCommand = 'docker compose --env-file ./runtime-secrets/runtime.env'
                    sh """
                        ${composeCommand} --profile opencode run --rm --entrypoint sh opencode -lc '
                            set -e
                            output=\$(npx -y @modelcontextprotocol/inspector --cli "http://mcp-gateway:3100/sse" --transport sse --method tools/list 2>&1)
                            echo "\$output" | grep -q "jenkins" || { echo "Missing jenkins tools in opencode container"; exit 1; }
                            echo "\$output" | grep -q "portainer" || { echo "Missing portainer tools in opencode container"; exit 1; }
                            echo "PASS | opencode container sees jenkins and portainer tools"
                        '
                    """
                }
            }
        }
    }
    
    post {
        unsuccessful {
            script {
                def composeCommand = fileExists('./runtime-secrets/runtime.env')
                    ? 'docker compose --env-file ./runtime-secrets/runtime.env'
                    : 'docker compose'
                sh script: "${composeCommand} down", returnStatus: true
            }
        }
        always {
            sh script: 'rm -rf ./runtime-secrets', returnStatus: true
        }
    }
}
