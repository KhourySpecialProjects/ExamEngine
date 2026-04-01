terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket = "examengine-terraform-state-staging"
    key    = "examengine/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

module "examengine" {
  source = "../../modules/examengine"

  aws_region        = var.aws_region
  environment       = var.environment
  domain_name       = var.domain_name
  deploy_branch     = var.deploy_branch
  bucket_name       = var.bucket_name
  db_instance_class = var.db_instance_class
  db_username       = var.db_username
  db_password       = var.db_password
  database_url      = var.database_url
  secret_key        = var.secret_key
  frontend_url      = var.frontend_url
}
