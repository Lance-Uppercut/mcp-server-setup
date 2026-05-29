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
                        [imageName: 'yahoo-mail-mcp', context: './servers/yahoo-mail-sse'],
                        [imageName: 'google-workspace-mcp', context: './servers/mcp-google-workspace'],
                        [imageName: 'tado-mcp', context: './servers/tado-mcp'],
                        [imageName: 'signal-mcp', context: './servers/signal-mcp'],
                        [imageName: 'todoist-mcp', context: './servers/todoist-mcp'],
                        [imageName: 'asus-router-mcp', context: './servers/asus-router-mcp'],
                        [imageName: 'portainer-mcp', context: './servers/portainer-mcp'],
                        [imageName: 'jenkins-mcp', context: './servers/jenkins-mcp']
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
                    } + [
                        usernamePassword(credentialsId: 'github', usernameVariable: 'GITHUB_REGISTRY_USER', passwordVariable: 'GITHUB_REGISTRY_TOKEN')
                    ]

                    withCredentials(credentialBindings) {
                        sh '''
                            mkdir -p ./runtime-secrets
                            chmod 700 ./runtime-secrets
                        '''

                        def runtimeEnvContent = runtimeEnvSpecs.collect { spec ->
                            "${spec.envName}=${quoteEnvValue(env."${spec.variable}")}"
                        }
                        runtimeEnvContent += "SIGNAL_BASE_URL=${quoteEnvValue('http://signal-proxy:8080')}"
                        runtimeEnvContent += "MCP_DATA_DIR=${quoteEnvValue(mcpDataDir)}"
                        runtimeEnvContent += "COMPOSE_PROJECT_NAME=${quoteEnvValue('mcp-servers')}"
                        runtimeEnvContent = runtimeEnvContent.join('\n') + '\n'

                        writeFile(file: './runtime-secrets/runtime.env', text: runtimeEnvContent)
                        sh 'chmod 600 ./runtime-secrets/runtime.env'

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

                        def stackName = 'mcp-servers'

                        sh '''
                            echo "$GITHUB_REGISTRY_TOKEN" | docker login ghcr.io --username "$GITHUB_REGISTRY_USER" --password-stdin
                        '''

                        sh """
                            mkdir -p '${mcpDataDir}/google-workspace/credentials' '${mcpDataDir}/tado'
                            install -m 600 "\$SECRET_GOOGLE_GAUTH_FILE" '${mcpDataDir}/google-workspace/.gauth.json'
                            install -m 600 "\$SECRET_GOOGLE_ACCOUNTS_FILE" '${mcpDataDir}/google-workspace/.accounts.json'

                            if [ -d ./runtime-secrets/google-oauth2-seed ]; then
                                for seedFile in ./runtime-secrets/google-oauth2-seed/.oauth2.*.json; do
                                    [ -f "\$seedFile" ] || continue
                                    seedName=\$(basename "\$seedFile")
                                    targetFile='${mcpDataDir}/google-workspace/credentials/'"\$seedName"
                                    if [ ! -f "\$targetFile" ]; then
                                        install -m 600 "\$seedFile" "\$targetFile"
                                    fi
                                done
                            fi

                            tadoTarget='${mcpDataDir}/tado/tokens.json'
                            if [ ! -f "\$tadoTarget" ]; then
                                install -m 600 "\$SECRET_TADO_TOKENS_FILE" "\$tadoTarget"
                            fi
                        """

                        timeout(time: 10, unit: 'MINUTES') {
                            sh '''
                                [ "$(docker info --format '{{.Swarm.LocalNodeState}}')" = "active" ] || docker swarm init >/dev/null
                                docker network inspect sentinel_sentinel-swarm-network >/dev/null 2>&1 || docker network create --driver overlay --attachable sentinel_sentinel-swarm-network
                                set -a
                                . ./runtime-secrets/runtime.env
                                set +a
                                docker stack deploy --with-registry-auth --prune -c docker-stack.yml -c docker-stack.build1.yml mcp-servers
                            '''
                        }

                        sh "docker stack services ${stackName}"

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
    }
    
    post {
        unsuccessful {
            script {
                sh script: 'docker stack services mcp-servers', returnStatus: true
            }
        }
        always {
            sh script: 'rm -rf ./runtime-secrets', returnStatus: true
        }
    }
}
