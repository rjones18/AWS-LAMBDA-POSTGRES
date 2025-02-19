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
    }]
  })
}

# ✅ IAM Policy for Lambda to Access RDS & S3
resource "aws_iam_policy" "lambda_policy" {
  name        = "lambda_rds_to_s3_policy"
  description = "Policy for Lambda to access RDS and S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["rds-db:connect"]
        Resource = "arn:aws:rds:${var.aws_region}:${var.aws_account_id}:db:${var.rds_instance_id}"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:*"
      }
    ]
  })
}

# ✅ Attach IAM Policy to Role
resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# ✅ S3 Bucket for Lambda Layer Storage
resource "aws_s3_bucket" "lambda_layers_bucket" {
  bucket = var.lambda_layer_s3_bucket
}

# ✅ Upload pg8000 Lambda Layer to S3
resource "aws_s3_object" "lambda_layer" {
  bucket = aws_s3_bucket.lambda_layers_bucket.id
  key    = "pg8000-layer.zip"
  source = "pg8000-layer.zip"
  etag   = filemd5("pg8000-layer.zip")
}

# ✅ Lambda Layer Definition
resource "aws_lambda_layer_version" "pg8000_layer" {
  layer_name          = "pg8000-layer"
  s3_bucket          = aws_s3_bucket.lambda_layers_bucket.id
  s3_key             = aws_s3_object.lambda_layer.key
  compatible_runtimes = ["python3.8", "python3.9", "python3.10", "python3.11"]
  description        = "pg8000 Lambda Layer for Amazon Linux 2"
}

# ✅ Zip and Deploy Lambda Function
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "lambda_function.py"
  output_path = "lambda_function.zip"
}

resource "aws_lambda_function" "rds_to_s3" {
  function_name    = "rds_to_s3_lambda"
  runtime         = "python3.9"
  handler         = "lambda_function.lambda_handler"
  role            = aws_iam_role.lambda_role.arn
  filename        = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout         = 30
  memory_size     = 512

  layers = [aws_lambda_layer_version.pg8000_layer.arn]
  
  environment {
    variables = {
      DB_HOST     = data.aws_db_instance.rds_instance.endpoint
      DB_NAME     = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_name"]
      DB_USER     = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_user"]
      DB_PASSWORD = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_password"]
      S3_BUCKET   = aws_s3_bucket.lambda_s3.bucket
      PYTHONPATH = "/opt/python"  # ✅ Ensure Lambda can import pg8000
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

