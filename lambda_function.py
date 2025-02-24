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
S3_BUCKET_NAME = os.getenv("S3_BUCKET")
S3_FILE_NAME = "rds_data.csv"

# ✅ Initialize S3 Resource
s3 = boto3.resource("s3")
bucket = s3.Bucket(S3_BUCKET_NAME)

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
        # ✅ Ensure `employees` table exists
        logger.info("Ensuring 'employees' table exists...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            email VARCHAR(100),
            hire_date DATE,
            department VARCHAR(50),
            salary DECIMAL(10,2)
        );
        """
        cursor.execute(create_table_query)
        conn.commit()

        # ✅ Insert sample data into employees table
        logger.info("Inserting employee data...")
        insert_data_query = """
        INSERT INTO employees (first_name, last_name, email, hire_date, department, salary)
        VALUES 
            ('Alice', 'Johnson', 'alice.johnson@example.com', '2023-05-10', 'Engineering', 80000.00),
            ('Bob', 'Smith', 'bob.smith@example.com', '2023-06-15', 'Marketing', 75000.00),
            ('Charlie', 'Brown', 'charlie.brown@example.com', '2023-07-01', 'HR', 70000.00)
        ON CONFLICT DO NOTHING;
        """
        cursor.execute(insert_data_query)
        conn.commit()

        logger.info("Querying database...")
        query = "SELECT * FROM employees;"
        cursor.execute(query)
        rows = cursor.fetchall()

        column_names = [desc[0] for desc in cursor.description]
        logger.info(f"Found {len(rows)} rows in 'employees' table.")

        # ✅ Write data to /tmp directory
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

