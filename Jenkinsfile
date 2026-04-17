@Library("shared-jenkins-pipelines") _

import groovy.json.JsonOutput
import groovy.json.JsonSlurperClassic

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
                        [imageName: 'tado-mcp-python', context: './servers/tado-mcp-python'],
                        [imageName: 'todoist-mcp', context: './servers/todoist-mcp'],
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
                            mkdir -p ./runtime-secrets ./data/google-workspace/credentials ./data/tado ./data/playwright
                            chmod 700 ./runtime-secrets
                        '''

                        def runtimeEnvContent = runtimeEnvSpecs.collect { spec ->
                            "${spec.envName}=${quoteEnvValue(env."${spec.variable}")}"
                        }.join('\n') + '\n'

                        writeFile(file: './runtime-secrets/runtime.env', text: runtimeEnvContent)
                        sh 'chmod 600 ./runtime-secrets/runtime.env'

                        sh """
                            install -m 600 '${env.SECRET_GOOGLE_GAUTH_FILE}' './data/google-workspace/.gauth.json'
                            install -m 600 '${env.SECRET_GOOGLE_ACCOUNTS_FILE}' './data/google-workspace/.accounts.json'
                        """

                        def googleOAuthSeed = readFile(env.SECRET_GOOGLE_OAUTH2_SEED_FILE).trim()
                        if (googleOAuthSeed) {
                            def parsedSeed = new JsonSlurperClassic().parseText(googleOAuthSeed)
                            if (!(parsedSeed instanceof Map)) {
                                error('Credential mcp-google-oauth2-seed-json must contain a JSON object keyed by .oauth2.*.json filenames.')
                            }

                            parsedSeed.each { filename, tokenPayload ->
                                if (!(filename instanceof String) || !filename.startsWith('.oauth2.') || !filename.endsWith('.json')) {
                                    error("Invalid Google OAuth seed filename: ${filename}")
                                }

                                def targetPath = "./data/google-workspace/credentials/${filename}"
                                if (!fileExists(targetPath)) {
                                    def renderedPayload = tokenPayload instanceof String
                                        ? tokenPayload
                                        : JsonOutput.prettyPrint(JsonOutput.toJson(tokenPayload))
                                    writeFile(
                                        file: targetPath,
                                        text: renderedPayload.endsWith('\n') ? renderedPayload : "${renderedPayload}\n"
                                    )
                                    sh "chmod 600 '${targetPath}'"
                                    echo "Seeded Google OAuth credentials at ${targetPath}"
                                }
                            }
                        }

                        if (!fileExists('./data/tado/tokens.json')) {
                            sh "install -m 600 '${env.SECRET_TADO_TOKENS_FILE}' './data/tado/tokens.json'"
                            echo 'Seeded Tado tokens at ./data/tado/tokens.json'
                        }

                        def composeCommand = 'docker compose --env-file ./runtime-secrets/runtime.env'

                        sh script: "${composeCommand} down --remove-orphans", returnStatus: true

                        timeout(time: 5, unit: 'MINUTES') {
                            sh "${composeCommand} pull"
                            sh "${composeCommand} up -d"
                        }

                        sh "${composeCommand} ps"

                        echo "Deployment complete!"
                    }
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
