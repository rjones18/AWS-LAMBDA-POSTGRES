import json
import string
import secrets
import boto3
import psycopg
import os
import logging
import botocore.exceptions

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables for DB connection
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  # The current password to connect to RDS

def generate_random_password(length=16):
    """
    Generates a random password using letters, digits, and selected punctuation.
    You can modify the character set or length as needed.
    """
    # Define an alphabet that avoids characters which may cause issues in SQL literals
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def lambda_handler(event, context):
    client = boto3.client('secretsmanager')
    
    # Replace with your secret name or ARN
    secret_id = 'arn:aws:secretsmanager:us-west-2:014498625953:secret:db-secret-0HOYKM'
    
    # Expect an event like:
    # {
    #     "update_key": "db_password",
    #     "new_value": "new_password_value"
    # }
    update_key = event.get('update_key', 'db_password')
    new_value = event.get('db_password', generate_random_password())
    
    # Update the secret in AWS Secrets Manager
    try:
        # Retrieve the current secret value (assumed to be a JSON string)
        get_response = client.get_secret_value(SecretId=secret_id)
        secret_string = get_response.get('SecretString', '{}')
        secret_dict = json.loads(secret_string)
        
        # Update the specific key with the new value
        secret_dict[update_key] = new_value
        
        # Save the updated secret back as a JSON string
        update_response = client.update_secret(
            SecretId=secret_id,
            SecretString=json.dumps(secret_dict)
        )
        logger.info("Secret updated successfully in Secrets Manager: %s", update_response)
        
    except Exception as e:
        logger.error("Error updating secret in Secrets Manager: %s", e)
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error updating secret: {str(e)}")
        }
    
    # Update the RDS DB password with the new value
    try:
        # Connect to the RDS PostgreSQL DB using the current credentials.
        # Note: DB_PASSWORD here is expected to be the current valid password.
        conn = psycopg.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        with conn:
            with conn.cursor() as cur:
                # Since we cannot parameterize identifiers or literals in a DDL command,
                # safely escape the new password by replacing single quotes with two single quotes.
                escaped_password = new_value.replace("'", "''")
                # Build the ALTER USER command. DB_USER is trusted from our environment.
                alter_query = f"ALTER USER {DB_USER} WITH PASSWORD '{escaped_password}';"
                cur.execute(alter_query)
                conn.commit()
                logger.info("RDS DB password updated successfully.")
    except Exception as db_err:
        logger.error("Error updating RDS DB password: %s", db_err)
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error updating RDS DB password: {str(db_err)}")
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps('Secret and RDS DB password updated successfully.')
    }