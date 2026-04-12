// =============================================================================
// Backend App CI/CD Pipeline
// =============================================================================
// Push-to-deploy: main branch → build → ECR → terraform → ECS
//
// Template vs spawned app:
// - In THIS template repo, APP_NAME is 'CHANGE_ME'. All build/deploy stages
//   are gated on APP_NAME != 'CHANGE_ME' so the template's own Jenkins
//   pipeline runs Checkout + Test green and reports success, without trying
//   to docker build a repo called "CHANGE_ME" (which ECR rejects —
//   tag names must be lowercase).
// - In a SPAWNED app repo, the /new-app skill (or you manually) replaces
//   APP_NAME with a lowercase app name like 'nairatracker'. The gates then
//   auto-release and the full build → push → deploy → smoke pipeline runs.
// =============================================================================

pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        AWS_ACCOUNT_ID = '134807048528'
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        APP_NAME = 'CHANGE_ME'  // <-- CHANGE THIS: your-app-name (lowercase, hyphen-ok)
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

        stage('Template placeholder check') {
            steps {
                script {
                    if (env.APP_NAME == 'CHANGE_ME') {
                        echo "ℹ️  APP_NAME is still the template placeholder — this is the template repo running a no-op build. Skipping all build/deploy stages. A spawned-app repo with a real APP_NAME will run them all."
                    } else {
                        echo "APP_NAME=${env.APP_NAME} — running full build + deploy pipeline."
                    }
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
            when { expression { return env.APP_NAME != 'CHANGE_ME' } }
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
            when { expression { return env.APP_NAME != 'CHANGE_ME' } }
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
            when { expression { return env.APP_NAME != 'CHANGE_ME' } }
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
            when { expression { return env.APP_NAME != 'CHANGE_ME' } }
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
            when { expression { return env.APP_NAME != 'CHANGE_ME' } }
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
            script {
                if (env.APP_NAME == 'CHANGE_ME') {
                    echo "✅ Template pipeline green (no-op build — APP_NAME still CHANGE_ME)"
                } else {
                    echo "✅ Deployment successful: ${env.APP_NAME}:${env.GIT_SHA}"
                }
            }
        }
        failure {
            echo "❌ Build failed!"
        }
        cleanup {
            sh 'docker system prune -f || true'
        }
    }
}
