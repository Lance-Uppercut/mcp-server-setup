@Library("shared-jenkins-pipelines") _

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
                    
                    def services = [
                        [name: 'tado-mcp-python', context: './servers/tado-mcp-python'],
                        [name: 'yahoo-mail-mcp', context: './servers/yahoo-mail-mcp-server']
                    ]
                    
                    services.each { service ->
                        buildAndPushImage(
                            registry: DOCKER_REGISTRY,
                            context: service.context,
                            name: service.name,
                            branch: sanitizedBranch,
                            sha: shortSha
                        )
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