pipeline {
    agent {
        label 'build'
        options {
            requiresBuildSlot true
        }
    }
    
    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build Docker images') {
            steps {
                sh 'docker compose build'
            }
        }
        
        stage('Start services') {
            steps {
                sh 'docker compose up -d'
            }
        }
        
        stage('Verify MCP servers') {
            steps {
                script {
                    def servers = ['yahoo-mail-mcp', 'alertmanager-mcp', 'tado-mcp']
                    servers.each { server ->
                        sh """
                            echo "Checking ${server}..."
                            docker ps --filter "name=${server}" --format "{{.Status}}"
                        """
                    }
                }
            }
        }
        
        stage('Test Tado SSE endpoint') {
            steps {
                sh '''
                    sleep 5
                    curl -s -X GET http://localhost:3102/sse -H "Accept: text/event-stream" --max-time 5 | head -1
                '''
            }
        }
    }
    
    post {
        always {
            sh 'docker compose down'
        }
    }
}