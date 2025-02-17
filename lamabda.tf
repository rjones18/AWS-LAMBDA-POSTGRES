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

# ✅ Upload Psycopg3 Lambda Layer to S3
resource "aws_s3_object" "lambda_layer" {
  bucket = aws_s3_bucket.lambda_layers_bucket.id
  key    = "psycopg3-layer.zip"
  source = "psycopg3-layer.zip"
  etag   = filemd5("psycopg3-layer.zip")
}

# ✅ Lambda Layer Definition
resource "aws_lambda_layer_version" "psycopg3_layer" {
  layer_name          = "psycopg3-layer"
  s3_bucket          = aws_s3_bucket.lambda_layers_bucket.id
  s3_key             = aws_s3_object.lambda_layer.key
  compatible_runtimes = ["python3.8", "python3.9", "python3.10", "python3.11"]
  description        = "Psycopg3 Lambda Layer for Amazon Linux 2"
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

  layers = [aws_lambda_layer_version.psycopg3_layer.arn]
  
  environment {
    variables = {
      DB_HOST     = var.rds_endpoint
      DB_NAME     = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_name"]
      DB_USER     = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_user"]
      DB_PASSWORD = jsondecode(nonsensitive(data.aws_secretsmanager_secret_version.current.secret_string))["db_password"]
      S3_BUCKET   = aws_s3_bucket.lambda_s3.bucket
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_attach]
}

# ✅ CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/rds_to_s3_lambda"
  retention_in_days = 14
}













