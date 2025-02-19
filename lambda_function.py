import json
import boto3
import pg8000
import csv
import os
from io import StringIO

# Environment variables for DB connection
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_FILE_NAME = "rds_data.csv"

def lambda_handler(event, context):
    try:
        # ✅ Connect to PostgreSQL RDS using pg8000
        conn = pg8000.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            ssl_context=True  # ✅ Ensures SSL connection
        )
        cursor = conn.cursor()

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
        
        # Commit the changes
        conn.commit()

        # ✅ Query the database
        query = "SELECT * FROM employees;"  # Change 'your_table' to your actual table name
        cursor.execute(query)
        rows = cursor.fetchall()

        # ✅ Get column names
        column_names = [desc[0] for desc in cursor.description]

        # ✅ Convert data to CSV
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(column_names)  # Write header
        csv_writer.writerows(rows)  # Write data

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

        return {
            "statusCode": 200,
            "body": json.dumps(f"Data successfully exported to s3://{S3_BUCKET}/{S3_FILE_NAME}")
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(str(e))
        }
