@Library("shared-jenkins-pipelines") _

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
                        [imageName: 'yahoo-mail-mcp-server', context: './servers/yahoo-mail-mcp-server']
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
                    
                    // Create persistent data directories
                    sh 'mkdir -p ./data/google-workspace ./data/tado'
                    
                    // Stop any existing containers first
                    sh script: 'docker compose down --remove-orphans', returnStatus: true
                    
                    // Pull latest images and start the stack with timeout
                    timeout(time: 5, unit: 'MINUTES') {
                        sh 'docker compose pull'
                        sh 'docker compose up -d'
                    }
                    
                    // Show running containers
                    sh 'docker compose ps'
                    
                    echo "Deployment complete!"
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