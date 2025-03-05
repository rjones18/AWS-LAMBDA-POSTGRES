import boto3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Clients
secretsmanager_client = boto3.client('secretsmanager')

# Rotation Lambda ARN to be attached to secrets
ROTATION_LAMBDA_ARN = "arn:aws:lambda:us-west-2:014498625953:function:rotate_rds_password_lambda"

def enable_rotation_and_attach_lambda():
    """Checks all secrets, enables rotation, and attaches the rotation Lambda."""
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
                        logger.info(f"Enabling rotation for secret: {secret_name}")

                        # Use rotate_secret to enable rotation and attach Lambda
                        secretsmanager_client.rotate_secret(
                            SecretId=secret_id,
                            RotationLambdaARN=ROTATION_LAMBDA_ARN
                        )
                        logger.info(f"Rotation enabled and Lambda attached for {secret_name}")

                    else:
                        logger.info(f"Rotation already enabled for secret: {secret_name}")

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
    enable_rotation_and_attach_lambda()
    return {
        "statusCode": 200,
        "body": "Secret rotation enabled and Lambda attached successfully."
    }


