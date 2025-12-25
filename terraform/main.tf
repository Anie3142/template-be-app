# =============================================================================
# Backend App - Terraform Configuration
# =============================================================================
# Uses terraform-ecs-app module for ECS deployment with Traefik routing
# =============================================================================

terraform {
  required_version = ">= 1.0"

  # Backend configuration - CHANGE for your app
  backend "s3" {
    bucket         = "nameless-terraform-state-911027631608"
    key            = "apps/CHANGE_ME/terraform.tfstate"  # <-- CHANGE THIS
    region         = "us-east-1"
    dynamodb_table = "nameless-terraform-locks"
    encrypt        = true
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
# Remote State References (from nameless-company-infra)
# -----------------------------------------------------------------------------
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "nameless-terraform-state-911027631608"
    key    = "live/10-network/terraform.tfstate"
    region = "us-east-1"
  }
}

data "terraform_remote_state" "ecs" {
  backend = "s3"
  config = {
    bucket = "nameless-terraform-state-911027631608"
    key    = "live/20-ecs/terraform.tfstate"
    region = "us-east-1"
  }
}

data "terraform_remote_state" "traefik" {
  backend = "s3"
  config = {
    bucket = "nameless-terraform-state-911027631608"
    key    = "live/27-traefik/terraform.tfstate"
    region = "us-east-1"
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
  default = "us-east-1"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "CHANGE_ME"  # <-- CHANGE THIS
}

variable "hostname" {
  description = "Public hostname for the app"
  type        = string
  default     = "CHANGE_ME.namelesscompany.cc"  # <-- CHANGE THIS
}

variable "image_tag" {
  description = "Docker image tag (set by CI/CD)"
  type        = string
  default     = "latest"
}

variable "ecr_registry" {
  default = "911027631608.dkr.ecr.us-east-1.amazonaws.com"
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
