pipeline {
    agent {
        label 'build'
    }
    
    options {
        requiresBuildSlot true
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }
    
    environment {
        DOCKER_REGISTRY = 'registry.hub.docker.com/soerendel'
        DOCKER_CREDENTIALS_ID = 'docker-hub-credentials'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build Docker images') {
            steps {
                script {
                    def branchName = env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '-')
                    def shortSha = sh(script: 'git rev-parse --short=5 HEAD', returnStdout: true).trim()
                    def tag = "${branchName}-${shortSha}"
                    
                    sh """
                        docker compose build
                        docker tag jenkins-mcp-spring:latest \${DOCKER_REGISTRY}/jenkins-mcp-spring:${tag}
                        docker tag tado-mcp-python:latest \${DOCKER_REGISTRY}/tado-mcp-python:${tag}
                        docker tag alertmanager-mcp:latest \${DOCKER_REGISTRY}/alertmanager-mcp:${tag}
                    """
                }
            }
        }
        
        stage('Push Docker images') {
            steps {
                script {
                    def branchName = env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '-')
                    def shortSha = sh(script: 'git rev-parse --short=5 HEAD', returnStdout: true).trim()
                    def tag = "${branchName}-${shortSha}"
                    
                    withDockerRegistry([credentialsId: DOCKER_CREDENTIALS_ID, url: 'https://index.docker.io/v1/']) {
                        sh """
                            docker push \${DOCKER_REGISTRY}/jenkins-mcp-spring:${tag}
                            docker push \${DOCKER_REGISTRY}/tado-mcp-python:${tag}
                            docker push \${DOCKER_REGISTRY}/alertmanager-mcp:${tag}
                        """
                    }
                }
            }
        }
    }
    
    post {
        always {
            sh 'docker compose down'
        }
    }
}