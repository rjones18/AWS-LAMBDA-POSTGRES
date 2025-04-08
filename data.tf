data "aws_secretsmanager_secret" "secrets" {
  arn = "arn:aws:secretsmanager:us-west-2:014498625953:secret:rds!db-67caeb76-069d-49e4-9807-067f875dbf3d-C5SI97"
}
data "aws_secretsmanager_secret_version" "current" {
  secret_id = data.aws_secretsmanager_secret.secrets.id
}
data "aws_db_instance" "rds_instance" {
  db_instance_identifier = var.rds_instance_id  # Use an input variable
}