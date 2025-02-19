import json
import boto3
import pg8000
import csv
import os
from io import StringIO
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
        logger.info("Starting database connection")
        # ✅ Connect to PostgreSQL RDS using pg8000
        conn = pg8000.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            ssl_context=True  # ✅ Ensures SSL connection
        )
        cursor = conn.cursor()

        logger.info("Creating table")
        # Create table if it doesn't exist
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
        
        logger.info("Inserting sample data")
        # Insert sample data
        insert_data_query = """
        INSERT INTO employees (first_name, last_name, email, hire_date, department, salary)
        VALUES 
            ('John', 'Doe', 'john.doe@example.com', '2023-01-15', 'Engineering', 75000.00),
            ('Jane', 'Smith', 'jane.smith@example.com', '2023-02-01', 'Marketing', 65000.00),
            ('Bob', 'Johnson', 'bob.johnson@example.com', '2023-03-10', 'Sales', 60000.00)
        ON CONFLICT DO NOTHING;
        """
        cursor.execute(insert_data_query)
        
        # Commit the changes
        conn.commit()

        logger.info("Querying database")
        # ✅ Query the database
        query = "SELECT * FROM employees;"
        cursor.execute(query)
        rows = cursor.fetchall()

        # ✅ Get column names
        column_names = [desc[0] for desc in cursor.description]

        logger.info(f"Found {len(rows)} rows")
        logger.info(f"Columns: {column_names}")

        # ✅ Convert data to CSV
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(column_names)  # Write header
        csv_writer.writerows(rows)  # Write data

        logger.info("Uploading to S3")
        # ✅ Upload CSV to S3
        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=S3_FILE_NAME,
            Body=csv_buffer.getvalue()
        )

        # ✅ Close connections
        cursor.close()
        conn.close()

        response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Data successfully exported to s3://{S3_BUCKET}/{S3_FILE_NAME}",
                "rows_processed": len(rows)
            })
        }
        logger.info(f"Success: {response}")
        return response

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "type": type(e).__name__
            })
        }

