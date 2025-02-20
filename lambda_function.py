import json
import boto3
import pg8000
import csv
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
DB_PASSWORD = os.getenv("DB_PASSWORD")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_FILE_NAME = "rds_data.csv"

# ✅ Set S3 upload timeout
S3_CLIENT = boto3.client("s3", config=boto3.session.Config(connect_timeout=5, read_timeout=5, retries={'max_attempts': 3}))

def lambda_handler(event, context):
    try:
        logger.info(f"Connecting to PostgreSQL: {DB_HOST}")
        conn = pg8000.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            ssl_context=True
        )
        cursor = conn.cursor()

        logger.info("Querying database...")
        query = "SELECT * FROM employees;"
        cursor.execute(query)
        rows = cursor.fetchall()

        column_names = [desc[0] for desc in cursor.description]
        logger.info(f"Found {len(rows)} rows in 'employees' table.")

        tmp_file_path = "/tmp/rds_data.csv"
        with open(tmp_file_path, "w", newline="") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(column_names)
            csv_writer.writerows(rows)

        # ✅ Check file size before upload
        file_size = os.path.getsize(tmp_file_path)
        logger.info(f"CSV file size: {file_size} bytes")

        # ✅ Use Multipart Upload for large files
        transfer_config = boto3.s3.transfer.TransferConfig(multipart_threshold=5 * 1024 * 1024)

        try:
            logger.info("Uploading to S3...")
            S3_CLIENT.upload_file(tmp_file_path, S3_BUCKET, S3_FILE_NAME, Config=transfer_config)
            logger.info(f"Successfully uploaded CSV to s3://{S3_BUCKET}/{S3_FILE_NAME}")
        except botocore.exceptions.EndpointConnectionError as e:
            logger.error("❌ Unable to reach S3! Check VPC settings or S3 VPC Endpoint.", exc_info=True)
            raise
        except botocore.exceptions.ClientError as e:
            logger.error(f"❌ AWS S3 Upload Failed: {e}", exc_info=True)
            raise

        cursor.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Data exported to s3://{S3_BUCKET}/{S3_FILE_NAME}",
                "rows_processed": len(rows)
            })
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "type": type(e).__name__
            })
        }
