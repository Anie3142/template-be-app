# Backend App Template

Self-contained Django/DRF backend template with push-to-deploy CI/CD.

## Quick Start

1. Clone this template for your new app
2. Search and replace `CHANGE_ME` with your app name
3. Add your Django code to `backend/`
4. Push to main → Jenkins builds → deploys to ECS

## Structure

```
├── Dockerfile          # Production multi-stage build
├── Jenkinsfile         # CI/CD pipeline
├── backend/            # Django application code
│   ├── manage.py
│   ├── config/         # Settings, URLs, WSGI
│   └── requirements.txt
├── docker/
│   └── entrypoint.sh   # Container startup script
└── terraform/
    └── main.tf         # Uses terraform-ecs-app module
```

## What to Change

1. `Jenkinsfile`: Set `APP_NAME`
2. `terraform/main.tf`: Set `app_name`, `hostname`, backend `key`
3. Add your SSM secrets to `terraform/main.tf`

## URLs

- App: `https://YOUR_APP.namelesscompany.cc`
- Jenkins: `https://jenkins.namelesscompany.cc`
