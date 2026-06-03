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
                        checkout scm
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
                        checkout scm
                    }
                }
                stage('Deploy stack') {
                    steps {
                        sh 'docker stack deploy --with-registry-auth --prune --detach=false -c docker-stack.yml -c docker-stack.build1.yml mcp-servers'
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