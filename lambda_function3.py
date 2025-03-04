import boto3
import json
import logging
import os
import psycopg  # PostgreSQL adapter for Python

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# AWS Clients
secretsmanager_client = boto3.client('secretsmanager')

# Retrieve environment variables
RDS_ADMIN_SECRET = os.getenv("arn:aws:secretsmanager:us-west-2:014498625953:secret:postgres-credentials-qBZ45r")  # ARN of the admin secret

def get_secret(secret_arn):
    """Retrieve secret from AWS Secrets Manager."""
    response = secretsmanager_client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])

def update_secret(secret_id, updated_secret):
    """Update the secret in AWS Secrets Manager with the new password."""
    secretsmanager_client.put_secret_value(
        SecretId=secret_id,
        SecretString=json.dumps(updated_secret),
        VersionStages=["AWSPENDING"]  # AWS requires AWSPENDING during rotation
    )
    logger.info(f"Updated secret in AWS Secrets Manager for {secret_id}")

def generate_new_password():
    """Generate a new secure password."""
    import secrets
    import string
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

def update_rds_password(db_host, db_port, dbname, db_user, new_password, admin_secret_arn):
    """Connects to RDS and updates the user password."""
    try:
        # Get admin credentials
        admin_secret = get_secret(admin_secret_arn)
        admin_user = admin_secret["db_user"]
        admin_password = admin_secret["db_password"]

        # Connect to RDS using admin credentials
        connection = psycopg.connect(
            dbname=dbname,
            user=admin_user,
            password=admin_password,
            host=db_host,
            port=db_port
        )
        connection.autocommit = True
        cursor = connection.cursor()

        # Update the password for the database user
        alter_query = f"ALTER USER {db_user} WITH PASSWORD '{new_password}';"
        cursor.execute(alter_query)

        logger.info(f"Successfully updated password for RDS user: {db_user}")

        # Close the connection
        cursor.close()
        connection.close()
    except Exception as e:
        logger.error(f"Error updating RDS password: {str(e)}")
        raise

def lambda_handler(event, context):
    """AWS Lambda function to rotate RDS passwords."""
    secret_id = event["SecretId"]
    step = event["Step"]

    logger.info(f"Processing rotation for {secret_id}, step: {step}")

    # Retrieve existing secret
    secret = get_secret(secret_id)

    # Extract necessary values
    db_host = secret["host"]
    db_port = secret.get("port", 5432)  # Default to PostgreSQL port
    dbname = secret["db_name"]
    db_user = secret["db_user"]
    new_password = generate_new_password()

    if step == "createSecret":
        # Update only the password, keeping other values the same
        secret["db_password"] = new_password
        update_secret(secret_id, secret)

    elif step == "setSecret":
        update_rds_password(db_host, db_port, dbname, db_user, new_password, RDS_ADMIN_SECRET)

    elif step == "testSecret":
        logger.info(f"Testing new password for {db_user} in {dbname}")

    elif step == "finishSecret":
        logger.info(f"Finalizing secret rotation for {secret_id}")

    return {
        "statusCode": 200,
        "body": "Secret rotation completed successfully."
    }

