terraform {
  backend "s3" {
    bucket         = "reggie-testing-bucket"
    key            = "Lambdas/terraform.tfstates"
    dynamodb_table = "terraform-lock"
  }
}