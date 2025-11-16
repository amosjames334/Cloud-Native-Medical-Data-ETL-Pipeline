"""
Unit tests for data loaders
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from src.loaders.s3_loader import S3Loader
import json
import io


class TestS3Loader:
    """Test S3 data loader"""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client"""
        with patch('src.loaders.s3_loader.boto3.client') as mock_client:
            yield mock_client.return_value
    
    def test_loader_initialization(self, mock_s3_client):
        """Test loader can be initialized"""
        loader = S3Loader('test-bucket', 'us-east-1')
        assert loader.bucket_name == 'test-bucket'
        assert loader.region == 'us-east-1'
    
    def test_read_json_success(self, mock_s3_client):
        """Test reading JSON from S3"""
        # Mock S3 response
        test_data = [{'id': 1, 'name': 'test'}]
        mock_response = {
            'Body': Mock()
        }
        mock_response['Body'].read.return_value = json.dumps(test_data).encode('utf-8')
        mock_s3_client.get_object.return_value = mock_response
        
        loader = S3Loader('test-bucket')
        result = loader.read_json('test/data.json')
        
        assert result == test_data
        mock_s3_client.get_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test/data.json'
        )
    
    def test_read_json_not_found(self, mock_s3_client):
        """Test reading non-existent JSON file"""
        # Mock NoSuchKey exception
        mock_s3_client.exceptions.NoSuchKey = Exception
        mock_s3_client.get_object.side_effect = mock_s3_client.exceptions.NoSuchKey
        
        loader = S3Loader('test-bucket')
        result = loader.read_json('nonexistent.json')
        
        assert result is None
    
    def test_write_json(self, mock_s3_client):
        """Test writing JSON to S3"""
        test_data = [{'id': 1, 'name': 'test'}]
        
        loader = S3Loader('test-bucket')
        loader.write_json(test_data, 'test/data.json')
        
        # Verify put_object was called
        assert mock_s3_client.put_object.called
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert call_args[1]['Key'] == 'test/data.json'
        assert call_args[1]['ContentType'] == 'application/json'
    
    def test_read_parquet_success(self, mock_s3_client):
        """Test reading Parquet from S3"""
        # Create sample DataFrame
        df = pd.DataFrame({'id': [1, 2], 'name': ['a', 'b']})
        
        # Convert to parquet bytes
        buffer = io.BytesIO()
        df.to_parquet(buffer, engine='pyarrow')
        parquet_bytes = buffer.getvalue()
        
        # Mock S3 response
        mock_response = {
            'Body': Mock()
        }
        mock_response['Body'].read.return_value = parquet_bytes
        mock_s3_client.get_object.return_value = mock_response
        
        loader = S3Loader('test-bucket')
        result = loader.read_parquet('test/data.parquet')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ['id', 'name']
    
    def test_read_parquet_not_found(self, mock_s3_client):
        """Test reading non-existent Parquet file"""
        mock_s3_client.exceptions.NoSuchKey = Exception
        mock_s3_client.get_object.side_effect = mock_s3_client.exceptions.NoSuchKey
        
        loader = S3Loader('test-bucket')
        result = loader.read_parquet('nonexistent.parquet')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_write_parquet(self, mock_s3_client):
        """Test writing Parquet to S3"""
        df = pd.DataFrame({'id': [1, 2], 'name': ['a', 'b']})
        
        loader = S3Loader('test-bucket')
        loader.write_parquet(df, 'test/data.parquet')
        
        # Verify put_object was called
        assert mock_s3_client.put_object.called
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert call_args[1]['Key'] == 'test/data.parquet'
    
    def test_read_csv_success(self, mock_s3_client):
        """Test reading CSV from S3"""
        df = pd.DataFrame({'id': [1, 2], 'name': ['a', 'b']})
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        
        mock_response = {
            'Body': Mock()
        }
        mock_response['Body'].read.return_value = csv_bytes
        mock_s3_client.get_object.return_value = mock_response
        
        loader = S3Loader('test-bucket')
        result = loader.read_csv('test/data.csv')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
    
    def test_write_csv(self, mock_s3_client):
        """Test writing CSV to S3"""
        df = pd.DataFrame({'id': [1, 2], 'name': ['a', 'b']})
        
        loader = S3Loader('test-bucket')
        loader.write_csv(df, 'test/data.csv')
        
        assert mock_s3_client.put_object.called
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]['ContentType'] == 'text/csv'
    
    def test_list_objects(self, mock_s3_client):
        """Test listing objects in S3"""
        mock_response = {
            'Contents': [
                {'Key': 'test/file1.json'},
                {'Key': 'test/file2.json'}
            ]
        }
        mock_s3_client.list_objects_v2.return_value = mock_response
        
        loader = S3Loader('test-bucket')
        result = loader.list_objects('test/')
        
        assert len(result) == 2
        assert 'test/file1.json' in result
        assert 'test/file2.json' in result
    
    def test_list_objects_empty(self, mock_s3_client):
        """Test listing objects with no results"""
        mock_s3_client.list_objects_v2.return_value = {}
        
        loader = S3Loader('test-bucket')
        result = loader.list_objects('test/')
        
        assert result == []
    
    def test_delete_object(self, mock_s3_client):
        """Test deleting object from S3"""
        loader = S3Loader('test-bucket')
        loader.delete_object('test/data.json')
        
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test/data.json'
        )
    
    def test_object_exists_true(self, mock_s3_client):
        """Test checking if object exists (exists)"""
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        
        loader = S3Loader('test-bucket')
        result = loader.object_exists('test/data.json')
        
        assert result is True
    
    def test_object_exists_false(self, mock_s3_client):
        """Test checking if object exists (doesn't exist)"""
        mock_s3_client.exceptions.ClientError = Exception
        mock_s3_client.head_object.side_effect = mock_s3_client.exceptions.ClientError
        
        loader = S3Loader('test-bucket')
        result = loader.object_exists('nonexistent.json')
        
        assert result is False
    
    def test_get_object_size(self, mock_s3_client):
        """Test getting object size"""
        mock_s3_client.head_object.return_value = {'ContentLength': 1024}
        
        loader = S3Loader('test-bucket')
        size = loader.get_object_size('test/data.json')
        
        assert size == 1024
    
    def test_get_object_size_not_found(self, mock_s3_client):
        """Test getting size of non-existent object"""
        mock_s3_client.exceptions.ClientError = Exception
        mock_s3_client.head_object.side_effect = mock_s3_client.exceptions.ClientError
        
        loader = S3Loader('test-bucket')
        size = loader.get_object_size('nonexistent.json')
        
        assert size is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])