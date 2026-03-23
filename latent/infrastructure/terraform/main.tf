# Latent Labs AWS Infrastructure
# GPU-enabled infrastructure for neural foundation model training and inference

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "latent-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "latent-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Latent"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "gpu_instance_type" {
  description = "GPU instance type for training/inference"
  type        = string
  default     = "g4dn.xlarge" # 1x T4 GPU, good for development
  # For production: p3.2xlarge (V100), p4d.24xlarge (A100)
}

variable "api_instance_type" {
  description = "Instance type for API servers"
  type        = string
  default     = "t3.medium"
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "latent-${var.environment}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "prod"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "latent-${var.environment}-vpc"
  }
}

# Security Groups
resource "aws_security_group" "api" {
  name_prefix = "latent-api-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for API servers"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "gpu" {
  name_prefix = "latent-gpu-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for GPU instances"

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Restrict in production
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name_prefix = "latent-db-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for database"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "latent-redis-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for Redis"

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id, aws_security_group.gpu.id]
  }
}

# RDS PostgreSQL
resource "aws_db_subnet_group" "main" {
  name       = "latent-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_db_instance" "main" {
  identifier             = "latent-${var.environment}"
  engine                 = "postgres"
  engine_version         = "16.1"
  instance_class         = var.environment == "prod" ? "db.r6g.large" : "db.t3.micro"
  allocated_storage      = 20
  max_allocated_storage  = 100
  storage_encrypted      = true
  db_name                = "latent"
  username               = "latent_admin"
  password               = random_password.db_password.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = var.environment != "prod"
  multi_az               = var.environment == "prod"

  backup_retention_period = var.environment == "prod" ? 7 : 1
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  performance_insights_enabled = var.environment == "prod"
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "main" {
  name       = "latent-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "latent-${var.environment}"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.environment == "prod" ? "cache.r6g.large" : "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
}

# S3 Buckets
resource "aws_s3_bucket" "models" {
  bucket = "latent-models-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "data" {
  bucket = "latent-data-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}

data "aws_caller_identity" "current" {}

# ECR Repositories
resource "aws_ecr_repository" "api" {
  name                 = "latent/api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "ml" {
  name                 = "latent/ml"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "latent/frontend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for EC2 GPU instances
resource "aws_iam_role" "gpu_instance" {
  name = "latent-gpu-instance-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "gpu_ecr" {
  role       = aws_iam_role.gpu_instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy" "gpu_s3" {
  name = "latent-gpu-s3-access"
  role = aws_iam_role.gpu_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.models.arn,
          "${aws_s3_bucket.models.arn}/*",
          aws_s3_bucket.data.arn,
          "${aws_s3_bucket.data.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "gpu" {
  name = "latent-gpu-profile-${var.environment}"
  role = aws_iam_role.gpu_instance.name
}

# Launch Template for GPU instances
resource "aws_launch_template" "gpu" {
  name_prefix   = "latent-gpu-"
  image_id      = data.aws_ami.deep_learning.id
  instance_type = var.gpu_instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.gpu.name
  }

  vpc_security_group_ids = [aws_security_group.gpu.id]

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 200
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -e

    # Install Docker
    yum update -y
    yum install -y docker
    systemctl start docker
    systemctl enable docker

    # Install NVIDIA Container Toolkit
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.repo | tee /etc/yum.repos.d/nvidia-docker.repo
    yum install -y nvidia-docker2
    systemctl restart docker

    # Login to ECR
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com

    # Pull and run ML service
    docker pull ${aws_ecr_repository.ml.repository_url}:latest
    docker run -d --gpus all \
      -p 8000:8000 \
      -e AWS_REGION=${var.aws_region} \
      -e S3_BUCKET=${aws_s3_bucket.models.bucket} \
      ${aws_ecr_repository.ml.repository_url}:latest
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "latent-gpu-${var.environment}"
    }
  }
}

# Deep Learning AMI
data "aws_ami" "deep_learning" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning AMI GPU PyTorch * (Amazon Linux 2) *"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "latent-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.api.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = var.environment == "prod"
}

resource "aws_lb_target_group" "api" {
  name        = "latent-api-${var.environment}"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 30
    interval            = 60
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.environment == "prod" ? aws_acm_certificate.main[0].arn : null

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  # Skip HTTPS listener in dev without cert
  count = var.environment == "prod" ? 1 : 0
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = var.environment == "prod" ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = var.environment == "prod" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    target_group_arn = var.environment != "prod" ? aws_lb_target_group.api.arn : null
  }
}

# ACM Certificate (production only)
resource "aws_acm_certificate" "main" {
  count             = var.environment == "prod" ? 1 : 0
  domain_name       = "api.latent.dev"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# ECS Cluster for API
resource "aws_ecs_cluster" "main" {
  name = "latent-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = var.environment == "prod" ? "FARGATE" : "FARGATE_SPOT"
    weight            = 1
  }
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "rds_endpoint" {
  value = aws_db_instance.main.endpoint
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "ecr_api_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_ml_url" {
  value = aws_ecr_repository.ml.repository_url
}

output "s3_models_bucket" {
  value = aws_s3_bucket.models.bucket
}

output "s3_data_bucket" {
  value = aws_s3_bucket.data.bucket
}

output "gpu_launch_template_id" {
  value = aws_launch_template.gpu.id
}
