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
                    def branchName = env.BRANCH_NAME ?: env.GIT_BRANCH ?: env.CHANGE_BRANCH
                    def sanitizedBranch = io.jenkins.pipeline.TagUtils.sanitizeTag(branchName ?: 'main')

                    def shortSha = sh(script: 'git rev-parse --short=5 HEAD', returnStdout: true).trim()
                    
                    echo "Building branch: ${sanitizedBranch}, SHA: ${shortSha}"
                    
                    def services = [
                        [imageName: 'mcp-google-workspace', context: './servers/mcp-google-workspace'],
                        [imageName: 'yahoo-mail-mcp-server', context: './servers/yahoo-mail-mcp-server']
                    ]
                    
                    echo "Services to build: ${services.collect { it.imageName }.join(', ')}"
                    
                    for (int i = 0; i < services.size(); i++) {
                        def service = services[i]
                        def currentImageName = service.imageName
                        def currentContext = service.context
                        echo "Building service ${i+1}/${services.size()}: ${currentImageName} with context: ${currentContext}"
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
    
    post {
        always {
            sh 'docker compose down'
        }
    }
}