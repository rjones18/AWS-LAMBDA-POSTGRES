import boto3
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Clients
secretsmanager_client = boto3.client("secretsmanager")

# Prefix for filtering secrets
SECRET_PREFIX = os.environ.get("SECRET_PREFIX", "rds!")  # You can hardcode if preferred
SCHEDULE_EXPRESSION = os.environ.get("SCHEDULE_EXPRESSION", "rate(8 hours)")
ROTATION_LAMBDA_ARN = os.environ.get("ROTATION_LAMBDA_ARN")  # Required for enabling rotation if not enabled

def get_prefixed_secrets():
    """Retrieves all secrets whose names start with the specified prefix."""
    try:
        paginator = secretsmanager_client.get_paginator("list_secrets")
        matched_secrets = []

        for page in paginator.paginate():
            for secret in page.get("SecretList", []):
                secret_name = secret.get("Name", "")
                if secret_name.startswith(SECRET_PREFIX):
                    logger.info(f"Matched secret with prefix: {secret_name}")
                    matched_secrets.append(secret["ARN"])

        logger.info(f"Found {len(matched_secrets)} secrets with prefix '{SECRET_PREFIX}'.")
        return matched_secrets

    except Exception as e:
        logger.error(f"Error retrieving secrets: {str(e)}")
        raise

def update_rotation_schedule(secret_arn):
    """Updates the rotation schedule using ScheduleExpression."""
    try:
        secret_metadata = secretsmanager_client.describe_secret(SecretId=secret_arn)

        if not secret_metadata.get("RotationEnabled", False):
            logger.info(f"Rotation is NOT enabled for secret: {secret_arn}. Skipping.")
            return

        current_expr = secret_metadata.get("RotationRules", {}).get("ScheduleExpression")

        if current_expr == SCHEDULE_EXPRESSION:
            logger.info(f"Schedule already set to '{SCHEDULE_EXPRESSION}' for {secret_arn}. Skipping.")
            return

        secretsmanager_client.rotate_secret(
            SecretId=secret_arn,
            RotationRules={
                "ScheduleExpression": SCHEDULE_EXPRESSION
            }
        )
        logger.info(f"Updated rotation schedule to '{SCHEDULE_EXPRESSION}' for secret: {secret_arn}")

    except secretsmanager_client.exceptions.ResourceNotFoundException:
        logger.warning(f"Secret not found: {secret_arn}")
    except secretsmanager_client.exceptions.InvalidRequestException as e:
        logger.error(f"Invalid request for secret {secret_arn}: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating rotation schedule for {secret_arn}: {str(e)}")

def lambda_handler(event, context):
    """Lambda function handler."""
    try:
        matching_secrets = get_prefixed_secrets()

        if not matching_secrets:
            logger.info(f"No secrets found with prefix '{SECRET_PREFIX}'.")
            return {"statusCode": 200, "body": f"No secrets found with prefix '{SECRET_PREFIX}'."}

        for secret_arn in matching_secrets:
            update_rotation_schedule(secret_arn)

        return {"statusCode": 200, "body": f"Rotation schedules updated for secrets with prefix '{SECRET_PREFIX}'."}

    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {"statusCode": 500, "body": f"Error during execution: {str(e)}"}








