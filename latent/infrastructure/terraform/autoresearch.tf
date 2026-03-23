# Compile Autoresearch - AWS GPU Infrastructure
# Deploys GPU instances for overnight autonomous research

# Variables
variable "autoresearch_enabled" {
  description = "Enable autoresearch GPU instances"
  type        = bool
  default     = false
}

variable "autoresearch_instance_count" {
  description = "Number of GPU instances for autoresearch"
  type        = number
  default     = 4
}

variable "autoresearch_instance_type" {
  description = "EC2 instance type for autoresearch"
  type        = string
  default     = "g4dn.xlarge"  # T4 GPU, cost-effective
  # Alternatives:
  # - g4dn.2xlarge: T4 + more CPU/memory
  # - p3.2xlarge: V100 (faster but more expensive)
  # - g5.xlarge: A10G (good balance)
}

variable "autoresearch_spot_enabled" {
  description = "Use spot instances for cost savings"
  type        = bool
  default     = true
}

variable "autoresearch_max_price" {
  description = "Max spot price (USD/hour)"
  type        = string
  default     = "0.50"  # g4dn.xlarge on-demand is ~$0.52
}

# Autoresearch Security Group
resource "aws_security_group" "autoresearch" {
  count = var.autoresearch_enabled ? 1 : 0

  name        = "${var.project_name}-autoresearch-sg"
  description = "Security group for autoresearch GPU instances"
  vpc_id      = aws_vpc.main.id

  # SSH access (for debugging)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Restrict in production!
  }

  # All outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-autoresearch-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# IAM Role for Autoresearch Instances
resource "aws_iam_role" "autoresearch" {
  count = var.autoresearch_enabled ? 1 : 0

  name = "${var.project_name}-autoresearch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# IAM Policy for S3 access (model checkpoints)
resource "aws_iam_role_policy" "autoresearch_s3" {
  count = var.autoresearch_enabled ? 1 : 0

  name = "${var.project_name}-autoresearch-s3"
  role = aws_iam_role.autoresearch[0].id

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
          "${aws_s3_bucket.models.arn}/*"
        ]
      }
    ]
  })
}

# Instance Profile
resource "aws_iam_instance_profile" "autoresearch" {
  count = var.autoresearch_enabled ? 1 : 0

  name = "${var.project_name}-autoresearch-profile"
  role = aws_iam_role.autoresearch[0].name
}

# Launch Template for Autoresearch Instances
resource "aws_launch_template" "autoresearch" {
  count = var.autoresearch_enabled ? 1 : 0

  name_prefix   = "${var.project_name}-autoresearch-"
  image_id      = data.aws_ami.deep_learning.id
  instance_type = var.autoresearch_instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.autoresearch[0].name
  }

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.autoresearch[0].id]
    subnet_id                   = aws_subnet.public[0].id
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 100  # GB
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -e

    # Update system
    sudo yum update -y

    # Clone the repository
    cd /home/ec2-user
    git clone https://github.com/yourusername/compile.git || true
    cd compile/ml/autoresearch

    # Setup Python environment
    source /opt/conda/bin/activate pytorch
    pip install -e .

    # Download MOABB data
    python prepare.py --dataset bnci2014001

    # Start autoresearch (will run until instance terminates)
    export CUDA_VISIBLE_DEVICES=0
    python orchestrator/coordinator.py --agents 1 --hours 8

    # Upload results to S3
    aws s3 sync ~/.cache/compile-autoresearch/ s3://${aws_s3_bucket.models.bucket}/autoresearch/

    # Self-terminate after completion (cost saving)
    sudo shutdown -h now
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "${var.project_name}-autoresearch"
      Project     = var.project_name
      Environment = var.environment
      Purpose     = "autoresearch"
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Spot Fleet Request (for multiple GPUs)
resource "aws_spot_fleet_request" "autoresearch" {
  count = var.autoresearch_enabled && var.autoresearch_spot_enabled ? 1 : 0

  iam_fleet_role                      = aws_iam_role.spot_fleet[0].arn
  target_capacity                     = var.autoresearch_instance_count
  terminate_instances_with_expiration = true
  valid_until                         = timeadd(timestamp(), "12h")  # 12 hour session

  launch_template_config {
    launch_template_specification {
      id      = aws_launch_template.autoresearch[0].id
      version = aws_launch_template.autoresearch[0].latest_version
    }
  }

  tags = {
    Name        = "${var.project_name}-autoresearch-fleet"
    Project     = var.project_name
    Environment = var.environment
  }
}

# IAM Role for Spot Fleet
resource "aws_iam_role" "spot_fleet" {
  count = var.autoresearch_enabled && var.autoresearch_spot_enabled ? 1 : 0

  name = "${var.project_name}-spot-fleet-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "spotfleet.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "spot_fleet" {
  count = var.autoresearch_enabled && var.autoresearch_spot_enabled ? 1 : 0

  role       = aws_iam_role.spot_fleet[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

# CloudWatch Alarm for cost monitoring
resource "aws_cloudwatch_metric_alarm" "autoresearch_cost" {
  count = var.autoresearch_enabled ? 1 : 0

  alarm_name          = "${var.project_name}-autoresearch-cost"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600  # 6 hours
  statistic           = "Maximum"
  threshold           = 50  # $50 alert

  dimensions = {
    Currency = "USD"
  }

  alarm_description = "Alert when autoresearch costs exceed $50"
  alarm_actions     = []  # Add SNS topic ARN for notifications

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Outputs
output "autoresearch_launch_template_id" {
  description = "Launch template ID for autoresearch instances"
  value       = var.autoresearch_enabled ? aws_launch_template.autoresearch[0].id : null
}

output "autoresearch_spot_fleet_id" {
  description = "Spot fleet request ID"
  value       = var.autoresearch_enabled && var.autoresearch_spot_enabled ? aws_spot_fleet_request.autoresearch[0].id : null
}
