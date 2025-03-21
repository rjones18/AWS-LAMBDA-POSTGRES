import boto3
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Clients
secretsmanager_client = boto3.client("secretsmanager")

# Rotation period (default: 8 days)
ROTATION_DAYS = int(os.environ.get("ROTATION_DAYS", "8"))

def get_rds_managed_secrets():
    """Retrieves all secrets managed by RDS."""
    try:
        paginator = secretsmanager_client.get_paginator("list_secrets")
        rds_secrets = []

        for page in paginator.paginate():
            for secret in page.get("SecretList", []):
                # Check if the secret is "Managed by RDS"
                if secret.get("OwningService") == "rds.amazonaws.com":
                    rds_secrets.append(secret["ARN"])

        logger.info(f"Found {len(rds_secrets)} RDS-managed secrets.")
        return rds_secrets

    except Exception as e:
        logger.error(f"Error retrieving secrets: {str(e)}")
        raise

def update_rotation_period(secret_arn):
    """Updates the rotation period for a given RDS-managed secret."""
    try:
        # Get current secret details
        secret_metadata = secretsmanager_client.describe_secret(SecretId=secret_arn)

        # Check if rotation is already enabled
        if not secret_metadata.get("RotationEnabled", False):
            logger.info(f"Rotation is NOT enabled for secret: {secret_arn}. Skipping.")
            return
        
        # Get current rotation period
        rotation_rules = secret_metadata.get("RotationRules", {})
        current_days = rotation_rules.get("AutomaticallyAfterDays")

        if current_days == ROTATION_DAYS:
            logger.info(f"Rotation period for {secret_arn} is already set to {ROTATION_DAYS} days. Skipping.")
            return

        # Update rotation period to 8 days
        secretsmanager_client.rotate_secret(
            SecretId=secret_arn,
            RotationRules={"AutomaticallyAfterDays": ROTATION_DAYS}
        )

        logger.info(f"Updated rotation period to {ROTATION_DAYS} days for secret: {secret_arn}")

    except secretsmanager_client.exceptions.ResourceNotFoundException:
        logger.warning(f"Secret not found: {secret_arn}")
    except secretsmanager_client.exceptions.InvalidRequestException as e:
        logger.error(f"Invalid request for secret {secret_arn}: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating rotation period for {secret_arn}: {str(e)}")

def lambda_handler(event, context):
    """Lambda function handler."""
    try:
        rds_secrets = get_rds_managed_secrets()
        
        if not rds_secrets:
            logger.info("No RDS-managed secrets found.")
            return {"statusCode": 200, "body": "No RDS-managed secrets found."}

        for secret_arn in rds_secrets:
            update_rotation_period(secret_arn)

        return {"statusCode": 200, "body": "Rotation periods updated for RDS-managed secrets."}

    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {"statusCode": 500, "body": f"Error during execution: {str(e)}"}
