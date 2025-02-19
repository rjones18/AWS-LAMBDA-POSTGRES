import json
import boto3
import psycopg
import csv
import os
from io import StringIO
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Starting Lambda execution")
    logger.info(f"Environment variables: DB_HOST={os.getenv('DB_HOST')}, DB_NAME={os.getenv('DB_NAME')}")
    
    try:
        # Log connection attempt
        logger.info(f"Attempting to connect to database at {os.getenv('DB_HOST')}")
        
        conn = psycopg.connect(
            host=os.getenv("DB_HOST"),
            port=5432,
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            sslmode='require'
        )
        
        logger.info("Database connection successful")
        cursor = conn.cursor()

        # Log table creation
        logger.info("Creating table if not exists")
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
        
        # Log data insertion
        logger.info("Inserting sample data")
        insert_data_query = """
        INSERT INTO employees (first_name, last_name, email, hire_date, department, salary)
        VALUES 
            ('John', 'Doe', 'john.doe@example.com', '2023-01-15', 'Engineering', 75000.00),
            ('Jane', 'Smith', 'jane.smith@example.com', '2023-02-01', 'Marketing', 65000.00),
            ('Bob', 'Johnson', 'bob.johnson@example.com', '2023-03-10', 'Sales', 60000.00)
        ON CONFLICT DO NOTHING;
        """
        cursor.execute(insert_data_query)
        conn.commit()
        logger.info("Data inserted successfully")

        # Log query execution
        logger.info("Executing SELECT query")
        query = "SELECT * FROM employees;"
        cursor.execute(query)
        rows = cursor.fetchall()
        logger.info(f"Query returned {len(rows)} rows")

        # Get column names
        column_names = [desc[0] for desc in cursor.description]
        logger.info(f"Column names: {column_names}")

        # Convert to CSV
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(column_names)
        csv_writer.writerows(rows)
        
        # Log S3 upload
        logger.info(f"Uploading to S3 bucket: {os.getenv('S3_BUCKET')}")
        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=os.getenv("S3_BUCKET"),
            Key="rds_data.csv",
            Body=csv_buffer.getvalue()
        )
        logger.info("S3 upload complete")

        # Close connections
        cursor.close()
        conn.close()
        logger.info("Database connections closed")

        response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Data exported to S3 bucket {os.getenv('S3_BUCKET')}",
                "rows_processed": len(rows)
            })
        }
        logger.info(f"Returning response: {response}")
        return response

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            
        error_response = {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "type": type(e).__name__
            })
        }
        logger.info(f"Returning error response: {error_response}")
        return error_response
