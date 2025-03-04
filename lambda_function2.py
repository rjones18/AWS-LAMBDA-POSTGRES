import boto3
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Clients
secretsmanager_client = boto3.client('secretsmanager')

# Environment variable for the rotation Lambda function (you need an existing rotation function)
ROTATION_LAMBDA_ARN = os.getenv("ROTATION_LAMBDA_ARN")

def enable_rotation():
    """Checks all secrets and enables rotation if not already enabled."""
    try:
        paginator = secretsmanager_client.get_paginator('list_secrets')
        secrets_list = []

        for page in paginator.paginate():
            secrets_list.extend(page.get('SecretList', []))

        for secret in secrets_list:
            secret_id = secret.get("ARN")
            secret_name = secret.get("Name")

            try:
                rotation_status = secretsmanager_client.describe_secret(SecretId=secret_id)
                if rotation_status.get("RotationEnabled", False):
                    logger.info(f"Rotation already enabled for secret: {secret_name}")
                    continue

                # Enable rotation with an 8-day period
                if ROTATION_LAMBDA_ARN:
                    logger.info(f"Enabling rotation for secret: {secret_name}")
                    secretsmanager_client.enable_rotation(
                        SecretId=secret_id,
                        RotationLambdaARN=ROTATION_LAMBDA_ARN,
                        RotationRules={"AutomaticallyAfterDays": 8}
                    )
                    logger.info(f"Rotation enabled for {secret_name} with a period of 8 days.")
                else:
                    logger.warning("Rotation Lambda ARN is not set. Cannot enable rotation.")

            except secretsmanager_client.exceptions.ResourceNotFoundException:
                logger.warning(f"Secret not found: {secret_name}")
            except Exception as e:
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

