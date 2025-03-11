import boto3
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Clients
secretsmanager_client = boto3.client('secretsmanager')

# Get Lambda ARNs from environment variables for better security
ROTATE_RDS_PASSWORD_LAMBDA_ARN = 'arn:aws:lambda:us-west-2:014498625953:function:rotate_rds_password_lambda'
ROTATION_DAYS = int(os.environ.get('ROTATION_DAYS', '8'))

def rotate_secret():
    """Checks all secrets and enables rotation if not already enabled."""
    try:
        paginator = secretsmanager_client.get_paginator('list_secrets')
        secrets_list = []

        for page in paginator.paginate():
            secrets_list.extend(page.get('SecretList', []))

        for secret in secrets_list:
            secret_id = secret.get("ARN")
            secret_name = secret.get("Name")

            if not secret_id or not secret_name:
                logger.warning("Skipping secret with missing ARN or Name")
                continue

            process_secret(secret_id, secret_name)

    except Exception as e:
        logger.error(f"Failed to list secrets: {str(e)}")
        raise

def process_secret(secret_id, secret_name):
    """Process individual secret for rotation setup."""
    try:
        # Get secret metadata
        secret_metadata = secretsmanager_client.describe_secret(SecretId=secret_id)
        
        # Check if rotation is already enabled
        if secret_metadata.get("RotationEnabled", False):
            logger.info(f"Rotation already enabled for secret: {secret_name}")
            return

        # Verify the Lambda ARN exists
        if not ROTATE_RDS_PASSWORD_LAMBDA_ARN:
            logger.error("Rotation Lambda ARN not configured in environment variables")
            return

        # Enable rotation
        secretsmanager_client.rotate_secret(
            SecretId=secret_id,
            RotationLambdaARN=ROTATE_RDS_PASSWORD_LAMBDA_ARN,
            RotationRules={
                "AutomaticallyAfterDays": ROTATION_DAYS
            }
        )
        
        logger.info(f"Successfully enabled rotation for {secret_name} with {ROTATION_DAYS} days rotation period")

    except secretsmanager_client.exceptions.ResourceNotFoundException:
        logger.warning(f"Secret not found: {secret_name}")
    except secretsmanager_client.exceptions.InvalidRequestException as e:
        logger.error(f"Invalid request for secret {secret_name}: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing secret {secret_name}: {str(e)}")

def lambda_handler(event, context):
    """Lambda function handler."""
    try:
        rotate_secret()
        return {
            "statusCode": 200,
            "body": "Secret rotation check and update completed successfully"
        }
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Error during execution: {str(e)}"
        }







