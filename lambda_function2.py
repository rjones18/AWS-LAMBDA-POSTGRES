import boto3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Secrets Manager client
secretsmanager_client = boto3.client('secretsmanager')

# Specify the ARN of your existing rotation Lambda function
ROTATION_LAMBDA_ARN = "arn:aws:lambda:region:account-id:function:your-rotation-lambda"

def check_and_enable_rotation():
    try:
        # List all secrets
        paginator = secretsmanager_client.get_paginator('list_secrets')
        secrets_list = []
        
        for page in paginator.paginate():
            secrets_list.extend(page.get('SecretList', []))
        
        for secret in secrets_list:
            secret_id = secret.get("ARN")
            secret_name = secret.get("Name")
            
            # Get secret rotation status
            try:
                rotation_status = secretsmanager_client.describe_secret(SecretId=secret_id)
                if rotation_status.get("RotationEnabled", False):
                    logger.info(f"Rotation is already enabled for secret: {secret_name}")
                    continue
                
                # Enable rotation with an 8-day period
                logger.info(f"Enabling rotation for secret: {secret_name}")
                secretsmanager_client.rotate_secret(
                    SecretId=secret_id,
                    RotationLambdaARN=ROTATION_LAMBDA_ARN
                )
                secretsmanager_client.update_secret_version_stage(
                    SecretId=secret_id,
                    VersionStage="AWSPENDING"
                )
                
                secretsmanager_client.put_secret_value(
                    SecretId=secret_id,
                    SecretString="{}"
                )

                secretsmanager_client.enable_rotation(
                    SecretId=secret_id,
                    RotationLambdaARN=ROTATION_LAMBDA_ARN,
                    RotationRules={"AutomaticallyAfterDays": 8}
                )

                logger.info(f"Rotation enabled for {secret_name} with a period of 8 days.")

            except secretsmanager_client.exceptions.ResourceNotFoundException:
                logger.warning(f"Secret not found: {secret_name}")
            except Exception as e:
                logger.error(f"Error processing secret {secret_name}: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to list secrets: {str(e)}")

def lambda_handler(event, context):
    check_and_enable_rotation()
    return {
        "statusCode": 200,
        "body": "Secret rotation check and update completed."
    }
