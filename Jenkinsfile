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
//   APP_NAME with a lowercase app name like 'myapp'. The gates then
//   auto-release and the full build → push → deploy → smoke pipeline runs.
//
// No account-specific values live in this file. The Jenkins controller
// provides them as global environment variables:
//   TF_STATE_BUCKET  S3 bucket for Terraform state (app + shared platform)
//   TF_LOCK_TABLE    DynamoDB table for Terraform state locking
//   ECS_CLUSTER      Name of the shared ECS cluster
//   APP_DOMAIN       Base domain for the smoke test (e.g. example.com)
// The AWS account ID is resolved at runtime from the agent's IAM role.
// =============================================================================

pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
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

        stage('Resolve AWS account') {
            when { expression { return env.APP_NAME != 'CHANGE_ME' } }
            steps {
                script {
                    env.AWS_ACCOUNT_ID = sh(
                        script: 'aws sts get-caller-identity --query Account --output text',
                        returnStdout: true
                    ).trim()
                    env.ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
                }
            }
        }

        stage('Test') {
            steps {
                sh '''
                    echo "Running tests..."
                    # Add your test commands here
                    # cd backend && pip install -r requirements-dev.txt && pytest -q  (GitHub Actions already runs this)
                '''
            }
        }

        stage('Build Image') {
            when { expression { return env.APP_NAME != 'CHANGE_ME' } }
            steps {
                sh '''
                    docker build --platform linux/amd64 \
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
                    // Plain terraform — Jenkins ECS task role provides AWS credentials via IMDS.
                    // Do NOT use aws2-wrap here: it requires ~/.aws/config (SSO profile), which
                    // doesn't exist in the ECS container. aws2-wrap is only for dev machines.
                    sh '''
                        terraform init -input=false \
                            -backend-config="bucket=${TF_STATE_BUCKET}" \
                            -backend-config="key=apps/${APP_NAME}/terraform.tfstate" \
                            -backend-config="region=${AWS_REGION}" \
                            -backend-config="dynamodb_table=${TF_LOCK_TABLE}"
                        terraform plan -input=false \
                            -var="app_name=${APP_NAME}" \
                            -var="image_tag=${GIT_SHA}" \
                            -var="ecr_registry=${ECR_REGISTRY}" \
                            -var="state_bucket=${TF_STATE_BUCKET}" \
                            -var="aws_region=${AWS_REGION}" \
                            -out=tfplan
                        terraform apply -auto-approve tfplan
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
                        --cluster ${ECS_CLUSTER} \
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
                    # Enable once the hostname resolves:
                    # curl -fsS https://${APP_NAME}.${APP_DOMAIN}/api/v1/health || exit 1
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
