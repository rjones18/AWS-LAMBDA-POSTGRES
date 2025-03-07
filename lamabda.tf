# ✅ Create an S3 Bucket for Lambda exports
resource "aws_s3_bucket" "lambda_s3" {
  bucket = var.s3_bucket_name
}


# ✅ IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_role" {
  name = "lambda_rds_to_s3_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    },
    {
        Effect = "Allow"
        Principal = { Service = "secretsmanager.amazonaws.com" }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# ✅ IAM Policy for Lambda to Access RDS & S3
resource "aws_iam_policy" "lambda_policy" {
  name        = "lambda_rds_to_s3_policy"
  description = "Policy for Lambda to access RDS, S3, and Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:PutObjectAcl", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}/*",
          "arn:aws:s3:::${var.s3_bucket_name}/"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["rds-db:connect"]
        Resource = "arn:aws:rds:${var.aws_region}:${var.aws_account_id}:db:${var.rds_instance_id}"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:ListSecrets",
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage",
          "secretsmanager:RotateSecret",
          "secretsmanager:EnableRotation",
          "secretsmanager:UpdateSecret"
        ]
        Resource = "*"
      },
            {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
        ]
        Resource = "*"
      }
    ]
  })
}


# ✅ Attach IAM Policy to Role
resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}


# In the source account (Account A) where the Lambda's IAM role is defined

# resource "aws_iam_role_policy" "lambda_assume_role_policy" {
#   name   = "LambdaAssumeRolePolicy"
#   role   = "lambda_rds_to_s3_role"  # Replace with your Lambda's IAM Role
#   policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
# }

# data "aws_iam_policy_document" "lambda_assume_role_policy" {
#   statement {
#     actions   = ["sts:AssumeRole"]
#     resources = ["arn:aws:iam::614768946157:role/CrossAccountRole"]  # Replace with the cross-account role ARN
#   }
# }


# ✅ S3 Bucket for Lambda Layer Storage
resource "aws_s3_bucket" "lambda_layers_bucket" {
  bucket = var.lambda_layer_s3_bucket
}

# # ✅ Upload pg8000 Lambda Layer to S3
# resource "aws_s3_object" "lambda_layer" {
#   bucket = aws_s3_bucket.lambda_layers_bucket.id
#   key    = "pg8000-layer.zip"
#   source = "pg8000-layer.zip"
#   etag   = filemd5("pg8000-layer.zip")
# }

# ✅ Upload psycopg3 Lambda Layer to S3
resource "aws_s3_object" "lambda_layer2" {
  bucket = aws_s3_bucket.lambda_layers_bucket.id
  key    = "psycopg-layer.zip"
  source = "psycopg-layer.zip"
  etag   = filemd5("psycopg-layer.zip")
}

# # ✅ Lambda Layer Definition
# resource "aws_lambda_layer_version" "pg8000_layer" {
#   layer_name          = "pg8000-layer"
#   s3_bucket          = aws_s3_bucket.lambda_layers_bucket.id
#   s3_key             = aws_s3_object.lambda_layer.key
#   compatible_runtimes = ["python3.8", "python3.9", "python3.10", "python3.11"]
#   description        = "pg8000 Lambda Layer for Amazon Linux 2"
# }

# ✅ Lambda Layer Definition
resource "aws_lambda_layer_version" "psycopg3_layer" {
  layer_name          = "psycopg3-layer"
  s3_bucket          = aws_s3_bucket.lambda_layers_bucket.id
  s3_key             = aws_s3_object.lambda_layer2.key
  compatible_runtimes = ["python3.8", "python3.9", "python3.10", "python3.11"]
  description        = "psycopg3 Lambda Layer for Amazon Linux 2"
}

# ✅ Zip and Deploy Lambda Function
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "lambda_function.py"
  output_path = "lambda_function.zip"
}

data "archive_file" "lambda_zip2" {
  type        = "zip"
  source_file = "lambda_function2.py"
  output_path = "lambda_function2.zip"
}

data "archive_file" "lambda_zip3" {
  type        = "zip"
  source_file = "lambda_function3.py"
  output_path = "lambda_function3.zip"
}


resource "aws_lambda_function" "check_secrets_rotation" {
  function_name    = "check_secrets_rotation_lambda"
  runtime         = "python3.9"
  handler         = "lambda_function2.lambda_handler"
  role            = aws_iam_role.lambda_role.arn
  filename        = data.archive_file.lambda_zip2.output_path
  source_code_hash = data.archive_file.lambda_zip2.output_base64sha256
  timeout         = 30
  memory_size     = 1024

  environment {
    variables = {
      ROTATION_LAMBDA_ARN = aws_lambda_function.rds_to_s3.arn
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_attach]
}


resource "aws_lambda_function" "rotation_rds_secret" {
  function_name    = "rotate_rds_password_lambda"
  runtime         = "python3.9"
  handler         = "lambda_function3.lambda_handler"
  role            = aws_iam_role.lambda_role.arn
  filename        = data.archive_file.lambda_zip3.output_path
  source_code_hash = data.archive_file.lambda_zip3.output_base64sha256
  timeout         = 30
  memory_size     = 1024

  layers = [aws_lambda_layer_version.psycopg3_layer.arn]
  
  vpc_config {
    subnet_ids         = ["subnet-02a65c02202c7c17f","subnet-008196eb2a85dec81"] # Add your private subnet IDs
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DB_HOST     = split(":", data.aws_db_instance.rds_instance.endpoint)[0]  # This will only take the hostname part
      DB_NAME     = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_name"]
      DB_USER     = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_user"]
      DB_PASSWORD = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_password"]
      S3_BUCKET   = aws_s3_bucket.lambda_s3.bucket
      PYTHONPATH = "/opt/python"  # ✅ Ensure Lambda can import pg8000
      LD_LIBRARY_PATH = "/opt/lib"
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_attach]
}

resource "aws_security_group" "lambda_sg" {
  name        = "lambda_sg"
  description = "Security group for Lambda function"
  vpc_id      = "vpc-09614cd61a9ffa007"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


resource "aws_lambda_function" "rds_to_s3" {
  function_name    = "rds_to_s3_lambda"
  runtime         = "python3.9"
  handler         = "lambda_function.lambda_handler"
  role            = aws_iam_role.lambda_role.arn
  filename        = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout         = 30
  memory_size     = 1024

  layers = [aws_lambda_layer_version.psycopg3_layer.arn]
  
  vpc_config {
    subnet_ids         = ["subnet-02a65c02202c7c17f","subnet-008196eb2a85dec81"] # Add your private subnet IDs
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DB_HOST     = split(":", data.aws_db_instance.rds_instance.endpoint)[0]  # This will only take the hostname part
      DB_NAME     = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_name"]
      DB_USER     = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_user"]
      DB_PASSWORD = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_password"]
      S3_BUCKET   = aws_s3_bucket.lambda_s3.bucket
      PYTHONPATH = "/opt/python"  # ✅ Ensure Lambda can import pg8000
      LD_LIBRARY_PATH = "/opt/lib"
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_attach]
}

# ✅ CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/rds_to_s3_lambda"
  retention_in_days = 14
}


# Step Function IAM Role
resource "aws_iam_role" "step_function_role" {
  name = "step_function_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# IAM Policy for Step Function to invoke Lambda
resource "aws_iam_policy" "step_function_policy" {
  name = "step_function_lambda_policy"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.rds_to_s3.arn
        ]
      }
    ]
  })
}

# Attach policy to Step Function role
resource "aws_iam_role_policy_attachment" "step_function_policy_attachment" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_policy.arn
}

# Step Function state machine
resource "aws_sfn_state_machine" "sfn_state_machine" {
  name     = "rds-to-s3-state-machine"
  role_arn = aws_iam_role.step_function_role.arn

  definition = jsonencode({
    Comment = "A state machine that invokes a Lambda function"
    StartAt = "InvokeLambda"
    States = {
      InvokeLambda = {
        Type = "Task"
        Resource = aws_lambda_function.rds_to_s3.arn
        End = true
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_function_logs.arn}:*"
    include_execution_data = true
    level                 = "ALL"
  }
}

# CloudWatch Log Group for Step Function
resource "aws_cloudwatch_log_group" "step_function_logs" {
  name              = "/aws/states/rds-to-s3-state-machine"
  retention_in_days = 14
}

# IAM Policy for Step Function logging
resource "aws_iam_policy" "step_function_logging_policy" {
  name = "step_function_logging_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutLogEvents",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach logging policy to Step Function role
resource "aws_iam_role_policy_attachment" "step_function_logging_attachment" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_logging_policy.arn
}

# Optional: Add CloudWatch Event Rule to trigger Step Function on a schedule
resource "aws_cloudwatch_event_rule" "step_function_trigger" {
  name                = "trigger-rds-to-s3-step-function"
  description         = "Trigger Step Function on a schedule"
  schedule_expression = "rate(1 day)" # Adjust as needed
}

resource "aws_cloudwatch_event_target" "step_function_target" {
  rule      = aws_cloudwatch_event_rule.step_function_trigger.name
  target_id = "StepFunctionTarget"
  arn       = aws_sfn_state_machine.sfn_state_machine.arn
  role_arn  = aws_iam_role.cloudwatch_role.arn
}

# IAM Role for CloudWatch Events
resource "aws_iam_role" "cloudwatch_role" {
  name = "cloudwatch_step_function_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# IAM Policy for CloudWatch to invoke Step Function
resource "aws_iam_policy" "cloudwatch_policy" {
  name = "cloudwatch_step_function_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "states:StartExecution"
      ]
      Resource = [
        aws_sfn_state_machine.sfn_state_machine.arn
      ]
    }]
  })
}

# Attach policy to CloudWatch role
resource "aws_iam_role_policy_attachment" "cloudwatch_policy_attachment" {
  role       = aws_iam_role.cloudwatch_role.name
  policy_arn = aws_iam_policy.cloudwatch_policy.arn
}


resource "aws_cloudwatch_event_rule" "check_secrets_rotation_schedule" {
  name                = "check-secrets-rotation-schedule"
  description         = "Run check_secrets_rotation_lambda every day"
  schedule_expression = "rate(1 day)" # Runs every 24 hours
}

resource "aws_cloudwatch_event_target" "check_secrets_rotation_target" {
  rule      = aws_cloudwatch_event_rule.check_secrets_rotation_schedule.name
  target_id = "LambdaCheckSecretsRotation"
  arn       = aws_lambda_function.check_secrets_rotation.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_invoke_check_secrets_rotation" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.check_secrets_rotation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.check_secrets_rotation_schedule.arn
}

resource "aws_cloudwatch_log_group" "check_secrets_rotation_logs" {
  name              = "/aws/lambda/check_secrets_rotation_lambda"
  retention_in_days = 14
}

resource "aws_lambda_permission" "allow_secrets_manager" {
  statement_id  = "AllowSecretsManagerInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.check_secrets_rotation.function_name
  principal     = "secretsmanager.amazonaws.com"
}

resource "aws_lambda_permission" "allow_secrets_manager_rotate" {
  statement_id  = "AllowSecretsManagerInvokeRotation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rotation_rds_secret.function_name
  principal     = "secretsmanager.amazonaws.com"
}
