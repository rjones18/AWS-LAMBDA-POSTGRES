import json
import boto3
import pg8000
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
IAM_ROLE_ARN = os.getenv("IAM_ROLE_ARN")  # RDS IAM Role for S3 export

def lambda_handler(event, context):
    try:
        logger.info(f"Connecting to PostgreSQL: {DB_HOST}")
        
        # ✅ Connect to PostgreSQL
        conn = pg8000.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            ssl_context=True
        )
        cursor = conn.cursor()

        # ✅ Run SQL query to export data directly to S3
        s3_file_path = f"s3://{S3_BUCKET}/employees_export.csv"

        export_query = f"""
        COPY (SELECT * FROM employees)
        TO '{s3_file_path}'
        WITH (FORMAT CSV, HEADER TRUE, IAM_ROLE '{IAM_ROLE_ARN}');
        """

        logger.info(f"Executing SQL Export to {s3_file_path}")
        cursor.execute(export_query)
        conn.commit()
        logger.info("✅ Export Successful!")

        # ✅ Close database connection
        cursor.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Data successfully exported to {s3_file_path}"
            })
        }

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


