# =============================================================================
# Backend App - Terraform Configuration
# =============================================================================
# Uses terraform-ecs-app module for ECS deployment with Traefik routing
# =============================================================================

terraform {
  required_version = ">= 1.0"

  # Partial S3 backend configuration. bucket / key / region / dynamodb_table are
  # supplied at init time so no account-specific values live in the repo:
  #   terraform init -backend-config=backend.hcl            (local, see backend.hcl.example)
  #   terraform init -backend-config="bucket=..." ...       (CI, see Jenkinsfile)
  backend "s3" {
    encrypt = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# Remote State References (shared platform stacks: network, ECS cluster, Traefik)
# -----------------------------------------------------------------------------
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "live/10-network/terraform.tfstate"
    region = var.aws_region
  }
}

data "terraform_remote_state" "ecs" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "live/20-ecs/terraform.tfstate"
    region = var.aws_region
  }
}

data "terraform_remote_state" "traefik" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "live/27-traefik/terraform.tfstate"
    region = var.aws_region
  }
}

# -----------------------------------------------------------------------------
# App Module
# -----------------------------------------------------------------------------
module "app" {
  source = "git::https://github.com/Anie3142/terraform-ecs-app.git?ref=v1.0.0"

  # App identity - CHANGE THESE
  app_name       = var.app_name
  hostname       = var.hostname
  container_port = 8000

  # Image from CI/CD
  image = "${var.ecr_registry}/${var.app_name}:${var.image_tag}"

  # Infrastructure references
  vpc_id                     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids                 = data.terraform_remote_state.network.outputs.private_subnet_ids
  cluster_arn                = data.terraform_remote_state.ecs.outputs.cluster_arn
  capacity_provider_name     = data.terraform_remote_state.ecs.outputs.apps_capacity_provider_name
  task_execution_role_arn    = data.terraform_remote_state.ecs.outputs.task_execution_role_arn
  traefik_security_group_ids = [data.terraform_remote_state.traefik.outputs.traefik_security_group_id]

  # Service Discovery
  enable_service_discovery = true
  cloudmap_namespace_id    = data.terraform_remote_state.network.outputs.cloudmap_namespace_id

  # Environment
  environment = {
    DJANGO_SETTINGS_MODULE = "config.settings.prod"
    ALLOWED_HOSTS          = var.hostname
  }

  # Secrets - add your SSM parameters here
  secrets = var.secrets

  # Resources
  cpu           = var.cpu
  memory        = var.memory
  desired_count = var.desired_count

  tags = {
    App         = var.app_name
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
variable "aws_region" {
  description = "AWS region for the app and the shared platform state"
  type        = string
  default     = "us-east-1"
}

variable "state_bucket" {
  description = "S3 bucket holding the shared platform remote state (network, ecs, traefik)"
  type        = string
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "CHANGE_ME" # <-- CHANGE THIS
}

variable "hostname" {
  description = "Public hostname for the app"
  type        = string
  default     = "CHANGE_ME.example.com" # <-- CHANGE THIS
}

variable "image_tag" {
  description = "Docker image tag (set by CI/CD)"
  type        = string
  default     = "latest"
}

variable "ecr_registry" {
  description = "ECR registry host, e.g. <account-id>.dkr.ecr.<region>.amazonaws.com (set by CI)"
  type        = string
}

variable "cpu" {
  default = 256
}

variable "memory" {
  default = 512
}

variable "desired_count" {
  default = 1
}

variable "secrets" {
  description = "SSM secrets map"
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "app_url" {
  value = module.app.app_url
}

output "service_name" {
  value = module.app.service_name
}
