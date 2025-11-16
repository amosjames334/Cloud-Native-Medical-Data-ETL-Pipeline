"""
S3 Data Loader
Handles reading and writing data to AWS S3
"""

import boto3
import pandas as pd
import json
import io
from typing import Optional, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class S3Loader:
    """Load and save data to S3"""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        """
        Initialize S3 loader
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        
        logger.info(f"Initialized S3Loader for bucket: {bucket_name}")
    
    def read_json(self, s3_key: str) -> Optional[list]:
        """
        Read JSON data from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            List of records or None if not found
        """
        try:
            logger.info(f"Reading JSON from s3://{self.bucket_name}/{s3_key}")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            logger.info(f"Successfully read {len(data)} records")
            return data
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Key not found: {s3_key}")
            return None
        except Exception as e:
            logger.error(f"Error reading JSON from S3: {e}")
            raise
    
    def write_json(self, data: Any, s3_key: str):
        """
        Write JSON data to S3
        
        Args:
            data: Data to write (must be JSON serializable)
            s3_key: S3 object key
        """
        try:
            logger.info(f"Writing JSON to s3://{self.bucket_name}/{s3_key}")
            
            json_str = json.dumps(data, default=str, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_str.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Successfully wrote JSON to {s3_key}")
            
        except Exception as e:
            logger.error(f"Error writing JSON to S3: {e}")
            raise
    
    def read_parquet(self, s3_key: str) -> pd.DataFrame:
        """
        Read Parquet data from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            DataFrame with data
        """
        try:
            logger.info(f"Reading Parquet from s3://{self.bucket_name}/{s3_key}")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            df = pd.read_parquet(io.BytesIO(response['Body'].read()))
            
            logger.info(f"Successfully read {len(df)} records")
            return df
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Key not found: {s3_key}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error reading Parquet from S3: {e}")
            raise
    
    def write_parquet(self, df: pd.DataFrame, s3_key: str):
        """
        Write DataFrame as Parquet to S3
        
        Args:
            df: DataFrame to write
            s3_key: S3 object key
        """
        try:
            logger.info(f"Writing Parquet to s3://{self.bucket_name}/{s3_key}")
            
            # Convert DataFrame to Parquet in memory
            buffer = io.BytesIO()
            df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
            buffer.seek(0)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType='application/octet-stream'
            )
            
            logger.info(f"Successfully wrote {len(df)} records to {s3_key}")
            
        except Exception as e:
            logger.error(f"Error writing Parquet to S3: {e}")
            raise
    
    def read_csv(self, s3_key: str) -> pd.DataFrame:
        """
        Read CSV data from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            DataFrame with data
        """
        try:
            logger.info(f"Reading CSV from s3://{self.bucket_name}/{s3_key}")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            df = pd.read_csv(io.BytesIO(response['Body'].read()))
            
            logger.info(f"Successfully read {len(df)} records")
            return df
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Key not found: {s3_key}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error reading CSV from S3: {e}")
            raise
    
    def write_csv(self, df: pd.DataFrame, s3_key: str):
        """
        Write DataFrame as CSV to S3
        
        Args:
            df: DataFrame to write
            s3_key: S3 object key
        """
        try:
            logger.info(f"Writing CSV to s3://{self.bucket_name}/{s3_key}")
            
            # Convert DataFrame to CSV in memory
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=csv_buffer.getvalue().encode('utf-8'),
                ContentType='text/csv'
            )
            
            logger.info(f"Successfully wrote {len(df)} records to {s3_key}")
            
        except Exception as e:
            logger.error(f"Error writing CSV to S3: {e}")
            raise
    
    def list_objects(self, prefix: str) -> list:
        """
        List objects in S3 with given prefix
        
        Args:
            prefix: S3 key prefix
            
        Returns:
            List of object keys
        """
        try:
            logger.info(f"Listing objects with prefix: {prefix}")
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            keys = [obj['Key'] for obj in response['Contents']]
            logger.info(f"Found {len(keys)} objects")
            
            return keys
            
        except Exception as e:
            logger.error(f"Error listing objects: {e}")
            raise
    
    def delete_object(self, s3_key: str):
        """
        Delete object from S3
        
        Args:
            s3_key: S3 object key
        """
        try:
            logger.info(f"Deleting s3://{self.bucket_name}/{s3_key}")
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Successfully deleted {s3_key}")
            
        except Exception as e:
            logger.error(f"Error deleting object: {e}")
            raise
    
    def object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists in S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except self.s3_client.exceptions.ClientError:
            return False
    
    def get_object_size(self, s3_key: str) -> Optional[int]:
        """
        Get size of object in bytes
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Size in bytes or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['ContentLength']
        except self.s3_client.exceptions.ClientError:
            return None


if __name__ == '__main__':
    # Test the S3 loader
    import os
    
    bucket = os.getenv('S3_BUCKET', 'test-bucket')
    loader = S3Loader(bucket)
    
    # Test write and read
    test_data = [{'id': 1, 'name': 'test'}]
    loader.write_json(test_data, 'test/data.json')
    
    result = loader.read_json('test/data.json')
    print(f"Read data: {result}")