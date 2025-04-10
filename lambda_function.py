import boto3
import psycopg
import csv
import os
import logging
import botocore.exceptions
import json  # Forgot to import json for error handling

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables for DB connection
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
S3_BUCKET_NAME = os.getenv("S3_BUCKET")
S3_FILE_NAME = "rds_data2.csv"

# ✅ Initialize S3 Resource
s3 = boto3.resource("s3")
bucket = s3.Bucket(S3_BUCKET_NAME)

def lambda_handler(event, context):
    try:
        logger.info(f"Connecting to PostgreSQL: {DB_HOST}")
        conn = psycopg.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode="require"
        )
        cursor = conn.cursor()

        # ✅ Query the pg_roles or pg_user table for roles (users)
        logger.info("Querying 'pg_roles' for user data...")
        query = "SELECT rolname, rolsuper, rolcanlogin, rolcreatedb, rolcreaterole FROM pg_roles;"
        cursor.execute(query)
        rows = cursor.fetchall()

        column_names = [desc.name for desc in cursor.description]
        logger.info(f"Found {len(rows)} roles in 'pg_roles'.")

        # ✅ Write data to /tmp directory as CSV
        tmp_file_path = "/tmp/rds_data.csv"
        with open(tmp_file_path, "w", newline="") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(column_names)
            csv_writer.writerows(rows)

        # ✅ Check if CSV file exists before uploading
        if not os.path.exists(tmp_file_path):
            logger.error(f"❌ CSV file not found: {tmp_file_path}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "CSV file not found before upload."})
            }

        # ✅ Use Multipart Upload for large files
        transfer_config = boto3.s3.transfer.TransferConfig(multipart_threshold=5 * 1024 * 1024)

        try:
            logger.info("Uploading to S3...")
            bucket.upload_file(tmp_file_path, S3_FILE_NAME, Config=transfer_config)
            logger.info(f"✅ Successfully uploaded CSV to s3://{S3_BUCKET_NAME}/{S3_FILE_NAME}")
        except botocore.exceptions.EndpointConnectionError as e:
            logger.error("❌ Unable to reach S3! Check VPC settings or S3 VPC Endpoint.", exc_info=True)
            raise
        except botocore.exceptions.ClientError as e:
            logger.error(f"❌ AWS S3 Upload Failed: {e}", exc_info=True)
            raise

        # ✅ Close database connection
        cursor.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Data exported to s3://{S3_BUCKET_NAME}/{S3_FILE_NAME}",
                "rows_processed": len(rows)
            })
        }

    except Exception as e:
        logger.error(f"❌ General Error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
