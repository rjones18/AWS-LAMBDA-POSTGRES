terraform {
  backend "s3" {
    bucket         = "reggie-testing-bucket"
    key            = "Lambdas2/terraform.tfstates"
    dynamodb_table = "terraform-lock"
  }
}