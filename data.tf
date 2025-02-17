data "aws_secretsmanager_secret" "secrets" {
  arn = "arn:aws:secretsmanager:us-west-2:014498625953:secret:postgres-credentials-qBZ45r"
}
data "aws_secretsmanager_secret_version" "current" {
  secret_id = data.aws_secretsmanager_secret.secrets.id
}
data "aws_db_instance" "rds_instance" {
  db_instance_identifier = var.rds_instance_id  # Use an input variable
}