# Infrastructure Migration Guide

This document covers all infrastructure changes made after commit `9c79a49` (pgadmin local dev setup, Feb 12 2026). None of these changes have been applied to a live environment yet.

The changes span 11 commits and represent a complete overhaul of the AWS architecture. This guide explains what changed, why, what risks exist, and the exact order to apply everything safely.

---

## What Changed: Overview

| Commit | Summary | Risk |
|--------|---------|------|
| `7fdfc15` | Custom VPC — replaces default VPC | Critical |
| `40c6cfc` | OIDC auth + Secrets Manager for credentials | High |
| `8e6be1f` | HTTP→HTTPS redirect on ALB, fix FRONTEND_URL protocol | Medium |
| `570eea3` | RDS encryption at rest | Critical |
| `ca00ce0` | VPC endpoint for Secrets Manager | Low |
| `803cef5` | `/health` endpoint + disable Swagger in production | Low |
| `f58eac2` | Restructure Terraform into module + per-environment roots | Critical |
| `f963e67` | Route53 hosted zone + automated ACM certificate | High |
| `18767a9` | Scope OIDC role to deploy branch, remove dead data sources | Low |
| `e46cb9d` | Replace CI/CD workflows with OIDC-based deploy pipelines | Medium |
| `2406e09` | Remove hardcoded AWS credentials from backend app | Low |

---

## What Changed and Why

The changes fall into four areas:

**Networking** — Replaced the default AWS VPC with a custom managed VPC. ECS tasks and RDS now run in private subnets with no public IPs. The ALB is the only internet-facing resource. NAT Gateways handle outbound access from ECS. VPC endpoints for S3, ECR, CloudWatch Logs, and Secrets Manager keep that traffic inside the VPC entirely. This is the standard production network topology — using the default VPC is an anti-pattern that leaks workloads onto a shared network.

**Credentials** — Eliminated all long-lived AWS keys. GitHub Actions now authenticates via OIDC (short-lived tokens, no stored secrets). ECS containers access S3 via the task IAM role (automatic credential injection by ECS). `DATABASE_URL` and `SECRET_KEY` moved from plaintext ECS environment variables into Secrets Manager. The backend app no longer requires `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` to be set — those fields were dead code that would have prevented startup on ECS anyway.

**Infrastructure management** — Terraform restructured from a flat layout into a reusable module (`modules/examengine/`) with separate environment roots (`environments/prod/`, `environments/staging/`), each with its own S3 state backend. Route53 and ACM are now managed by Terraform with automated DNS certificate validation. SSM Parameter Store populated with the values CI/CD needs (cluster name, service names, ECR URIs, domain), so those aren't hardcoded anywhere.

**Application fixes** — Two bugs resolved: the Dockerfile healthcheck pointed to `/docs` which is disabled in production (would cause containers to fail their healthcheck and restart-loop); and the backend required `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` as required config fields that were never used, which would have caused startup failures on ECS.
j
**What to be careful about:** RDS encryption cannot be enabled in-place — Terraform will destroy and recreate the instance, which means data loss if the database already has content. The VPC change forces recreation of the ALB, ECS services, and RDS (new subnets, new VPC). The Terraform restructure changes all resource addresses to `module.examengine.*` — if there is existing state, it must be migrated or Terraform will destroy and recreate everything.

---

## Migration Execution Plan

Since none of this has been applied, everything goes in one pass. Follow this exact order.

### Before You Start

```bash
# 1. Confirm you have CLI access to the correct AWS account
aws sts get-caller-identity

# 2. Create Terraform state S3 buckets if they don't exist
# Prod:
aws s3 mb s3://examengine-terraform-state --region us-east-1
# Staging:
aws s3 mb s3://examengine-terraform-state-staging --region us-east-1

# 3. Enable versioning on state buckets
aws s3api put-bucket-versioning \
  --bucket examengine-terraform-state \
  --versioning-configuration Status=Enabled

# 4. Create ECR repositories if they don't exist
aws ecr create-repository --repository-name fastapi-backend
aws ecr create-repository --repository-name next-web
```

### Step 1 — Configure Variables

```bash
cd infrastructure/terraform/environments/prod
cp ../terraform.tfvars.example terraform.tfvars
```

Fill in `terraform.tfvars`:

```hcl
aws_region        = "us-east-1"
environment       = "prod"
domain_name       = "examengine.yourdomain.com"
frontend_url      = "https://examengine.yourdomain.com"
bucket_name       = "examengine-datasets-prod"
db_instance_class = "db.t3.small"
db_username       = "postgres"
db_password       = "strong-password-here"
database_url      = "postgresql+psycopg2://postgres:strong-password-here@PLACEHOLDER:5432/exam_engine_db"
secret_key        = "<run: openssl rand -hex 32>"
deploy_branch     = "main"
```

> `database_url` uses `PLACEHOLDER` for now — the RDS endpoint isn't known until after apply. You'll update it in Step 4.

### Step 2 — Apply Infrastructure

```bash
terraform init
terraform plan   # Review carefully — expect ~60+ resources to be created
terraform apply
```

This creates: VPC, subnets, NAT gateways, VPC endpoints, ALB, ECS cluster + services, RDS, S3, Route53 zone, ACM certificate, Secrets Manager entries, SSM parameters, and the GitHub Actions IAM role.

### Step 3 — Update DNS at Registrar

```bash
terraform output route53_nameservers
```

Add the 4 nameservers as NS records for your domain at your registrar (e.g. Porkbun). Wait 5–30 minutes for propagation.

ACM certificate validation is automated via Route53 — once the nameservers propagate, the certificate will validate automatically. You can monitor:

```bash
aws acm describe-certificate \
  --certificate-arn $(terraform output -raw certificate_arn) \
  --query 'Certificate.Status'
```

### Step 4 — Update database_url with Real RDS Endpoint

```bash
terraform output rds_endpoint
```

Update `terraform.tfvars`:

```hcl
database_url = "postgresql+psycopg2://postgres:strong-password-here@<rds_endpoint>:5432/exam_engine_db"
```

Then apply again to push the correct value into Secrets Manager:

```bash
terraform apply
```

### Step 5 — Add GitHub Repository Secrets

```bash
terraform output github_actions_role_arn
```

In GitHub → Repository Settings → Secrets and Variables → Actions:

| Secret | Value |
|--------|-------|
| `AWS_GITHUB_ACTIONS_ROLE_ARN_PROD` | Output from prod `terraform output github_actions_role_arn` |
| `AWS_GITHUB_ACTIONS_ROLE_ARN_STAGING` | Output from staging environment (repeat steps 1–4 for staging) |

Remove any old secrets if they exist:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `FRONTEND_URL` (now comes from SSM)

### Step 6 — Trigger First Deployment

Push to `main` to trigger `deploy-prod.yml`:

```bash
git push origin main
```

The workflow will:
1. Assume the OIDC role
2. Read cluster name, service names, ECR URIs, and domain from SSM
3. Build and push backend + frontend images to ECR
4. Force-deploy both ECS services

Monitor in GitHub Actions and CloudWatch:

```bash
aws logs tail /ecs/examengine-backend-prod --follow
aws logs tail /ecs/examengine-frontend-prod --follow
```

### Step 7 — Verify

```bash
# Check ECS services are stable
aws ecs describe-services \
  --cluster ee-cluster \
  --services examengine-backend-service-prod examengine-frontend-service-prod \
  --query 'services[*].{name:serviceName,status:status,running:runningCount,desired:desiredCount}'

# Check backend health
curl https://examengine.yourdomain.com/api/health

# Check HTTP redirects to HTTPS
curl -I http://examengine.yourdomain.com
# Expect: HTTP/1.1 301 Moved Permanently
```

---

## Key Things to Watch Out For

**RDS is brand new.** The database schema is created automatically by `init_db()` on first backend startup. No data exists yet — that's expected.

**NAT Gateways cost ~$35/month each** (2 are created). For staging you may want to reduce to 1 AZ. Edit `vpc.tf` and reduce the `count` on `aws_nat_gateway` and `aws_eip` from `length(var.availability_zones)` to `1`.

**The OIDC trust policy is scoped to the repo and branch.** If the GitHub org or repo name ever changes from `KhourySpecialProjects/ExamEngine`, the IAM role trust policy must be updated or deployments will fail with an access denied error.

**Secrets Manager secrets are populated by Terraform** using the `database_url` and `secret_key` variables. If you rotate the DB password, you must update `terraform.tfvars` and run `terraform apply` — or update the secret value directly in the console and redeploy the ECS service.

**Swagger is disabled in production.** The environment variable `ENVIRONMENT=production` in the ECS task definition triggers this. In staging (`ENVIRONMENT=staging`) Swagger remains accessible.

**ECR repositories are `data` sources — they must exist before `terraform apply`.** If they don't exist, the plan will fail with a "repository not found" error. Create them manually first (see Step 0 above).
