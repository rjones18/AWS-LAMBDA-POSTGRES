import boto3
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Clients
secretsmanager_client = boto3.client("secretsmanager")

# Environment Variables
SECRET_ID = os.environ.get("SECRET_ID")  # The specific secret to manage
ROTATE_RDS_PASSWORD_LAMBDA_ARN = os.environ.get("ROTATION_LAMBDA_ARN")  # Lambda ARN for rotation
ROTATION_DAYS = int(os.environ.get("ROTATION_DAYS", "8"))  # Rotation period

def rotate_secret(secret_id):
    """Checks the specific secret and enables rotation if not already enabled."""
    try:
        # Validate that SECRET_ID is provided
        if not secret_id:
            logger.error("No SECRET_ID provided in environment variables")
            return

        logger.info(f"Checking rotation status for secret: {secret_id}")

        # Get secret metadata
        secret_metadata = secretsmanager_client.describe_secret(SecretId=secret_id)

        # Check if rotation is already enabled
        if secret_metadata.get("RotationEnabled", False):
            logger.info(f"Rotation already enabled for secret: {secret_id}")
            return

        # Verify the Lambda ARN exists
        if not ROTATE_RDS_PASSWORD_LAMBDA_ARN:
            logger.error("Rotation Lambda ARN not configured in environment variables")
            return

        # Enable rotation
        secretsmanager_client.rotate_secret(
            SecretId=secret_id,
            RotationLambdaARN=ROTATE_RDS_PASSWORD_LAMBDA_ARN,
            RotationRules={"AutomaticallyAfterDays": ROTATION_DAYS},
        )

        logger.info(f"Successfully enabled rotation for secret: {secret_id} with {ROTATION_DAYS} days rotation period")

    except secretsmanager_client.exceptions.ResourceNotFoundException:
        logger.warning(f"Secret not found: {secret_id}")
    except secretsmanager_client.exceptions.InvalidRequestException as e:
        logger.error(f"Invalid request for secret {secret_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing secret {secret_id}: {str(e)}")

def lambda_handler(event, context):
    """Lambda function handler."""
    try:
        rotate_secret(SECRET_ID)
        return {
            "statusCode": 200,
            "body": "Secret rotation check and update completed successfully",
        }
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Error during execution: {str(e)}",
        }













