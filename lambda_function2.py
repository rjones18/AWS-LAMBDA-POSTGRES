import boto3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Secrets Manager Client
secretsmanager_client = boto3.client('secretsmanager')

def enable_rotation():
    """Checks all secrets and enables rotation if not already enabled."""
    try:
        paginator = secretsmanager_client.get_paginator('list_secrets')
        
        for page in paginator.paginate():
            for secret in page.get('SecretList', []):
                secret_id = secret.get("ARN")
                secret_name = secret.get("Name")

                try:
                    # Check if rotation is already enabled
                    rotation_status = secretsmanager_client.describe_secret(SecretId=secret_id)
                    if rotation_status.get("RotationEnabled", False):
                        logger.info(f"Rotation already enabled for secret: {secret_name}")
                        continue

                    # Enable rotation with an 8-day rotation period
                    logger.info(f"Enabling rotation for secret: {secret_name}")
                    secretsmanager_client.enable_rotation(
                        SecretId=secret_id,
                        RotationRules={"AutomaticallyAfterDays": 8}
                    )
                    logger.info(f"Rotation enabled for {secret_name} with a period of 8 days.")

                except secretsmanager_client.exceptions.ResourceNotFoundException:
                    logger.warning(f"Secret not found: {secret_name}")
                except secretsmanager_client.exceptions.ClientError as e:
                    if "InvalidRequestException" in str(e):
                        logger.warning(f"Secret {secret_name} does not support rotation.")
                    else:
                        logger.error(f"Error processing secret {secret_name}: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to list secrets: {str(e)}")

def lambda_handler(event, context):
    """Lambda function handler."""
    enable_rotation()
    return {
        "statusCode": 200,
        "body": "Secret rotation check and update completed."
    }

