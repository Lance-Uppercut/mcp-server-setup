@Library('shared-jenkins-pipelines@main') _

pipeline {
    agent none
    environment {
        DOCKER_REGISTRY = 'registry:5000'
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {
        stage('Build and Push Docker images') {
            agent { label 'build' }
            stages {
                stage('Checkout') {
                    steps {
                        deleteDir()
                        checkout scm
                        script {
                            env.BUILD_NODE_NAME = env.NODE_NAME
                            currentBuild.displayName = "#${env.BUILD_NUMBER} [build:${env.BUILD_NODE_NAME}]"
                        }
                    }
                }
                stage('Build MCP Servers') {
                    steps {
                        sh '''
                            docker compose build \
                                yahoo-mail-mcp \
                                google-workspace-mcp \
                                tado-mcp \
                                signal-mcp \
                                slack-mcp \
                                todoist-mcp \
                                asus-router-mcp \
                                portainer-build1 \
                                portainer-build2 \
                                portainer-monitor \
                                portainer-observability1 \
                                portainer-tools1 \
                                portainer-production1 \
                                jenkins-mcp
                        '''
                    }
                }
                stage('Push Docker images') {
                    steps {
                        sh '''
                            docker compose push \
                                yahoo-mail-mcp \
                                google-workspace-mcp \
                                tado-mcp \
                                signal-mcp \
                                slack-mcp \
                                todoist-mcp \
                                asus-router-mcp \
                                portainer-build1 \
                                portainer-build2 \
                                portainer-monitor \
                                portainer-observability1 \
                                portainer-tools1 \
                                portainer-production1 \
                                jenkins-mcp
                        '''
                    }
                }
            }
        }
        stage('Deploy') {
            agent { label 'build && swarm-manager-build' }
            stages {
                stage('Checkout') {
                    steps {
                        deleteDir()
                        checkout scm
                        script {
                            env.DEPLOY_NODE_NAME = env.NODE_NAME
                            currentBuild.displayName = "#${env.BUILD_NUMBER} [build:${env.BUILD_NODE_NAME ?: '-'} deploy:${env.DEPLOY_NODE_NAME}]"
                        }
                    }
                }
                stage('Deploy stack') {
                    steps {
                        withCredentials([
                            string(credentialsId: 'mcp-jenkins-url', variable: 'MCP_JENKINS_URL'),
                            string(credentialsId: 'mcp-jenkins-username', variable: 'MCP_JENKINS_USERNAME'),
                            string(credentialsId: 'mcp-jenkins-api-token', variable: 'MCP_JENKINS_API_TOKEN'),
                            string(credentialsId: 'slack-bot-token', variable: 'MCP_SLACK_BOT_TOKEN')
                        ]) {
                            withEnv([
                                'JENKINS_URL=' + env.MCP_JENKINS_URL,
                                'JENKINS_USERNAME=' + env.MCP_JENKINS_USERNAME,
                                'JENKINS_API_TOKEN=' + env.MCP_JENKINS_API_TOKEN,
                                'SLACK_BOT_TOKEN=' + env.MCP_SLACK_BOT_TOKEN
                            ]) {
                                sh '''
                                    HOST_MCP_DATA_DIR="/home/jenkins/mcp-server-setup-data"
                                    docker run --rm -v "${HOST_MCP_DATA_DIR}:/host-data" alpine:3.20 \
                                        sh -c 'mkdir -p /host-data/google-workspace /host-data/tado /host-data/signal-cli /host-data/playwright'
                                '''
                                sh '''
                                    for attempt in 1 2 3; do
                                        if MCP_DATA_DIR="/home/jenkins/mcp-server-setup-data" docker stack deploy --with-registry-auth --prune --detach=false -c docker-stack.yml -c docker-stack.build1.yml mcp-servers; then
                                            exit 0
                                        fi

                                        if [ "$attempt" -lt 3 ]; then
                                            echo "Deploy attempt $attempt failed; waiting 20 seconds before retry"
                                            sleep 20
                                        fi
                                    done

                                    exit 1
                                '''
                            }
                        }
                    }
                }
                stage('Verify MCP servers') {
                    steps {
                        sh 'chmod +x ./scripts/verify-mcp-servers.sh'
                        sh script: './scripts/verify-mcp-servers.sh', returnStatus: true
                    }
                }
            }
        }
    }
}
