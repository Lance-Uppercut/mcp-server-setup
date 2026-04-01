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
        DOCKER_REGISTRY = 'registry.hub.docker.com'
        DOCKER_NAMESPACE = 'soerendel'
        DOCKER_CREDENTIALS_ID = 'docker-hub-credentials'
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
                    def gitHash = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    
                    echo "Building branch: ${sanitizedBranch}, SHA: ${shortSha}"
                    
                    withDockerRegistry([credentialsId: DOCKER_CREDENTIALS_ID, url: 'https://index.docker.io/v1/']) {
                        def services = [
                            [name: 'tado-mcp-python', context: './servers/tado-mcp-python'],
                            [name: 'yahoo-mail-mcp', context: './servers/yahoo-mail-mcp-server']
                        ]
                        
                        services.each { service ->
                            def imageName = "${DOCKER_NAMESPACE}/${service.name}"
                            
                            sh """
                                docker buildx inspect codex-builder >/dev/null 2>&1 || docker buildx create --name codex-builder --driver docker-container --use
                                docker buildx use codex-builder
                                
                                docker buildx build --pull --push \
                                    --platform linux/amd64,linux/arm64 \
                                    -t ${DOCKER_REGISTRY}/${imageName}:${sanitizedBranch} \
                                    -t ${DOCKER_REGISTRY}/${imageName}:${shortSha} \
                                    -t ${DOCKER_REGISTRY}/${imageName}:${gitHash} \
                                    -t ${DOCKER_REGISTRY}/${imageName}:latest \
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