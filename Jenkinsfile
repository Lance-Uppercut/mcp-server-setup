@Library('shared-jenkins-pipelines@main') _

pipeline {
    agent none
    environment {
        DOCKER_REGISTRY = 'ioffearegistry.azurecr.io'
        IMAGE_TAG = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
        REPO_NAME = 'mcp-server-setup'
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {
        stage('Build and Push Docker images') {
            agent { label 'build' }
            environment {
                DOCKER_BUILDKIT = '1'
            }
            stages {
                stage('Checkout') {
                    steps {
                        checkout scm
                    }
                }
                stage('Build MCP Servers') {
                    steps {
                        sh '''
                            docker compose build mcp-supervisor
                            docker compose build mcp-supervisor-test
                        '''
                    }
                }
                stage('Push Docker images') {
                    when {
                        expression { env.BRANCH_NAME == 'main' || env.BRANCH_NAME.startsWith('feat/') }
                    }
                    steps {
                        sh '''
                            docker login "${DOCKER_REGISTRY}" -u "$(vault kv get -field=username "${DOCKER_REGISTRY}")" -p "$(vault kv get -field=password "${DOCKER_REGISTRY}")"
                            docker compose push mcp-supervisor
                            docker compose push mcp-supervisor-test
                        '''
                    }
                }
            }
        }
        stage('Deploy') {
            agent { label 'build && swarm-manager-build' }
            stages {
                stage('Deploy stack') {
                    environment {
                        MCP_VERSION = "${IMAGE_TAG}"
                    }
                    steps {
                        sh 'MCP_VERSION="${MCP_VERSION}" docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml mcp'
                    }
                }
                stage('Verify MCP servers') {
                    steps {
                        sh 'sleep 5 && docker service ls --filter name=mcp_'
                    }
                }
            }
        }
    }
}