# S3 Bucket for Lambda exports
resource "aws_s3_bucket" "lambda_s3" {
  bucket = "my-lambda-export-bucket"
}

# IAM Role for Lambda
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

# IAM Policy for Lambda to access S3 and RDS
resource "aws_iam_policy" "lambda_policy" {
  name        = "lambda_rds_to_s3_policy"
  description = "Policy for Lambda to access RDS and S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "arn:aws:s3:::my-lambda-export-bucket/*"
      },
      {
        Effect   = "Allow"
        Action   = ["rds-db:connect"]
        Resource = "arn:aws:rds:us-east-1:123456789012:db:my-rds-instance"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:us-east-1:123456789012:*"
      }
    ]
  })
}

# Attach IAM policy to role
resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# ✅ Lambda Layer for psycopg2
data "archive_file" "psycopg2_layer" {
  type        = "zip"
  source_dir  = "psycopg2_layer"  # Ensure this directory contains psycopg2 installed files
  output_path = "psycopg2_layer.zip"
}

resource "aws_lambda_layer_version" "psycopg2_layer" {
  filename            = data.archive_file.psycopg2_layer.output_path
  layer_name          = "psycopg2-binary-layer"
  compatible_runtimes = ["python3.9"]
}

# ✅ Zip and Deploy Lambda Function
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "lambda_function.py"  # Ensure this file exists locally
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

  layers = [aws_lambda_layer_version.psycopg2_layer.arn]
  
  environment {
    variables = {
      DB_HOST   = "edu.cd282sms4zh3.us-west-2.rds.amazonaws.com"
      DB_NAME   = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_name"]
      DB_USER   = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_user"]
      DB_PASSWORD =jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_password"]
      S3_BUCKET = aws_s3_bucket.lambda_s3.bucket
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_attach]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/rds_to_s3_lambda"
  retention_in_days = 14
}












