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
        DOCKER_REGISTRY = 'registry:5000'
        DOCKER_CREDENTIALS_ID = 'registry-credentials'
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
                    def branchName = env.BRANCH_NAME
                    def sanitizedBranch = branchName.toLowerCase().replaceAll(/[^a-z0-9_.-]/, '-')
                    def shortSha = sh(script: 'git rev-parse --short=5 HEAD', returnStdout: true).trim()
                    
                    echo "Building branch: ${sanitizedBranch}, SHA: ${shortSha}"
                    
                    withCredentials([usernamePassword(credentialsId: DOCKER_CREDENTIALS_ID, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                        sh "docker login ${DOCKER_REGISTRY} --username \$DOCKER_USER --password \$DOCKER_PASS"
                        
                        def services = [
                            [name: 'tado-mcp-python', context: './servers/tado-mcp-python'],
                            [name: 'yahoo-mail-mcp', context: './servers/yahoo-mail-mcp-server']
                        ]
                        
                        services.each { service ->
                            sh """
                                docker buildx inspect mcp-builder >/dev/null 2>&1 || docker buildx create --name mcp-builder --driver docker-container --use
                                docker buildx use mcp-builder
                                
                                docker buildx build --pull --push \
                                    -t ${DOCKER_REGISTRY}/${service.name}:${sanitizedBranch} \
                                    -t ${DOCKER_REGISTRY}/${service.name}:${shortSha} \
                                    -t ${DOCKER_REGISTRY}/${service.name}:latest \
                                    ${service.context}
                            """
                        }
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