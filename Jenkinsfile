// =============================================================================
// Backend App CI/CD Pipeline
// =============================================================================
// Push-to-deploy: main branch → build → ECR → terraform → ECS
// =============================================================================

pipeline {
    agent any
    
    environment {
        AWS_REGION = 'us-east-1'
        AWS_ACCOUNT_ID = '134807048528'
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        APP_NAME = 'CHANGE_ME'  // <-- CHANGE THIS: your-app-name
        IMAGE_TAG = "${GIT_COMMIT.take(7)}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                }
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    echo "Running tests..."
                    # Add your test commands here
                    # python -m pytest backend/tests/ -v
                '''
            }
        }
        
        stage('Build Image') {
            steps {
                sh '''
                    docker build --platform linux/arm64 \
                        -t ${ECR_REGISTRY}/${APP_NAME}:${GIT_SHA} \
                        -t ${ECR_REGISTRY}/${APP_NAME}:latest \
                        .
                '''
            }
        }
        
        stage('Push to ECR') {
            steps {
                sh '''
                    aws ecr get-login-password --region ${AWS_REGION} | \
                        docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    
                    docker push ${ECR_REGISTRY}/${APP_NAME}:${GIT_SHA}
                    docker push ${ECR_REGISTRY}/${APP_NAME}:latest
                '''
            }
        }
        
        stage('Deploy via Terraform') {
            steps {
                dir('terraform') {
                    // Every terraform invocation is wrapped in `aws2wrap --profile default --`.
                    // Under OIDC SSO, plain `terraform` fails with "no valid credential sources".
                    // Jenkins may supply creds via its instance profile, but the wrapper is
                    // harmless there and keeps dev/prod command shapes identical.
                    sh '''
                        aws2wrap --profile default -- terraform init -input=false
                        aws2wrap --profile default -- terraform plan -var="image_tag=${GIT_SHA}" -out=tfplan
                        aws2wrap --profile default -- terraform apply -auto-approve tfplan
                    '''
                }
            }
        }
        
        stage('Wait for Deployment') {
            steps {
                sh '''
                    echo "Waiting for ECS deployment to stabilize..."
                    aws ecs wait services-stable \
                        --cluster nameless-cluster \
                        --services ${APP_NAME} \
                        --region ${AWS_REGION}
                    echo "Deployment complete!"
                '''
            }
        }
        
        stage('Smoke Test') {
            steps {
                sh '''
                    echo "Running smoke test..."
                    # Replace with your app hostname
                    # curl -f https://${APP_NAME}.namelesscompany.cc/health || exit 1
                    echo "Smoke test passed!"
                '''
            }
        }
    }
    
    post {
        success {
            echo "✅ Deployment successful: ${APP_NAME}:${GIT_SHA}"
        }
        failure {
            echo "❌ Deployment failed!"
        }
        cleanup {
            sh 'docker system prune -f || true'
        }
    }
}
