import string
import secrets
import boto3
import psycopg
import os
import json
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables for DB connection
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")

# Secrets Manager details
SECRET_ID = "arn:aws:secretsmanager:us-west-2:014498625953:secret:test-db-secret-lMtizF"

def generate_random_password(length=16):
    """
    Generates a random password using letters, digits, and selected punctuation.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_current_db_password():
    """
    Fetches the current database password from AWS Secrets Manager.
    """
    client = boto3.client("secretsmanager")

    try:
        response = client.get_secret_value(SecretId=SECRET_ID)
        secret_string = response.get("SecretString", "{}")
        secret_dict = json.loads(secret_string)

        return secret_dict.get("db_password")
    except Exception as e:
        logger.error(f"Error retrieving secret from Secrets Manager: {e}")
        raise RuntimeError("Failed to retrieve DB password from Secrets Manager")

def update_secret(new_password):
    """
    Updates the AWS Secrets Manager secret with the new database password.
    """
    client = boto3.client("secretsmanager")

    try:
        # Get the current secret value
        response = client.get_secret_value(SecretId=SECRET_ID)
        secret_dict = json.loads(response.get("SecretString", "{}"))

        # Update the password in the secret
        secret_dict["db_password"] = new_password

        client.update_secret(
            SecretId=SECRET_ID,
            SecretString=json.dumps(secret_dict),
        )
        logger.info("Secret updated successfully in Secrets Manager.")
    except Exception as e:
        logger.error(f"Error updating secret in Secrets Manager: {e}")
        raise RuntimeError("Failed to update AWS Secrets Manager")

def update_db_password(old_password, new_password):
    """
    Connects to the RDS database using the current password and updates it to the new password.
    """
    try:
        conn = psycopg.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=old_password  # Using the retrieved current password
        )
        with conn:
            with conn.cursor() as cur:
                escaped_password = new_password.replace("'", "''")
                alter_query = f"ALTER USER {DB_USER} WITH PASSWORD '{escaped_password}';"
                cur.execute(alter_query)
                conn.commit()
                logger.info("RDS DB password updated successfully.")
    except Exception as db_err:
        logger.error(f"Error updating RDS DB password: {db_err}")
        raise RuntimeError("Failed to update RDS DB password")

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    """
    # Step 1: Retrieve the current password from Secrets Manager
    current_db_password = get_current_db_password()

    if not current_db_password:
        return {
            "statusCode": 500,
            "body": json.dumps("Error: Could not retrieve current DB password")
        }

    # Step 2: Generate a new password
    new_db_password = generate_random_password()

    # Step 3: Update the RDS database password using the current password
    try:
        update_db_password(current_db_password, new_db_password)
    except RuntimeError as e:
        return {"statusCode": 500, "body": json.dumps(str(e))}

    # Step 4: Update the new password in Secrets Manager
    try:
        update_secret(new_db_password)
    except RuntimeError as e:
        return {"statusCode": 500, "body": json.dumps(str(e))}

    return {
        "statusCode": 200,
        "body": json.dumps("RDS DB password updated successfully and Secrets Manager updated.")
    }