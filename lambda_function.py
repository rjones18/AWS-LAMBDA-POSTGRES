import json
import boto3
import pg8000
import csv
import os
import logging

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

def lambda_handler(event, context):
    try:
        logger.info(f"Connecting to PostgreSQL: {DB_HOST}")
        # ✅ Connect to PostgreSQL RDS using pg8000
        conn = pg8000.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            ssl_context=True  # ✅ Ensures SSL connection
        )
        cursor = conn.cursor()

        logger.info("Querying database...")
        query = "SELECT * FROM employees;"  # ✅ Only query data
        cursor.execute(query)
        rows = cursor.fetchall()

        # ✅ Get column names
        column_names = [desc[0] for desc in cursor.description]
        logger.info(f"Found {len(rows)} rows in 'employees' table.")

        # ✅ Save to temporary file in Lambda's /tmp directory
        tmp_file_path = "/tmp/rds_data.csv"
        with open(tmp_file_path, "w", newline="") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(column_names)  # Write headers
            csv_writer.writerows(rows)  # Write rows

        # ✅ Upload to S3
        s3_client = boto3.client("s3")
        s3_client.upload_file(tmp_file_path, S3_BUCKET, S3_FILE_NAME)
        logger.info(f"Successfully uploaded CSV to s3://{S3_BUCKET}/{S3_FILE_NAME}")

        # ✅ Close connections
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


