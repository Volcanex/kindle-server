"""
File Handler Utility
Handles file operations for Google Cloud Storage integration
"""

import os
import hashlib
import logging
import tempfile
from typing import Optional, Dict, List, Union
from datetime import datetime, timedelta
import mimetypes

# Google Cloud Storage
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound

from config.settings import Config

logger = logging.getLogger(__name__)

class FileHandler:
    """Utility class for handling file operations with Google Cloud Storage"""
    
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket_name = Config.GCS_BUCKET_NAME
        self.bucket = self.storage_client.bucket(self.bucket_name)
    
    def upload_file(self, file_path: str, gcs_path: str, content_type: str = None) -> bool:
        """
        Upload a file to Google Cloud Storage
        
        Args:
            file_path: Local file path
            gcs_path: Destination path in GCS
            content_type: MIME type of the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            # Determine content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(file_path, content_type=content_type)
            
            logger.info(f"Uploaded file to GCS: {file_path} -> {gcs_path}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error uploading file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def upload_content(self, content: Union[str, bytes], gcs_path: str, content_type: str = None) -> bool:
        """
        Upload content directly to Google Cloud Storage
        
        Args:
            content: Content to upload (string or bytes)
            gcs_path: Destination path in GCS
            content_type: MIME type of the content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(gcs_path)
            
            if isinstance(content, str):
                blob.upload_from_string(content, content_type=content_type or 'text/plain')
            else:
                blob.upload_from_string(content, content_type=content_type or 'application/octet-stream')
            
            logger.info(f"Uploaded content to GCS: {gcs_path}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error uploading content: {e}")
            return False
        except Exception as e:
            logger.error(f"Error uploading content: {e}")
            return False
    
    def download_file(self, gcs_path: str, local_path: str) -> bool:
        """
        Download a file from Google Cloud Storage
        
        Args:
            gcs_path: Source path in GCS
            local_path: Destination local file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(gcs_path)
            
            if not blob.exists():
                logger.error(f"File not found in GCS: {gcs_path}")
                return False
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            blob.download_to_filename(local_path)
            
            logger.info(f"Downloaded file from GCS: {gcs_path} -> {local_path}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error downloading file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    def download_content(self, gcs_path: str) -> Optional[bytes]:
        """
        Download content from Google Cloud Storage as bytes
        
        Args:
            gcs_path: Source path in GCS
            
        Returns:
            File content as bytes, or None if failed
        """
        try:
            blob = self.bucket.blob(gcs_path)
            
            if not blob.exists():
                logger.error(f"File not found in GCS: {gcs_path}")
                return None
            
            content = blob.download_as_bytes()
            logger.info(f"Downloaded content from GCS: {gcs_path}")
            return content
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error downloading content: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading content: {e}")
            return None
    
    def delete_file(self, gcs_path: str) -> bool:
        """
        Delete a file from Google Cloud Storage
        
        Args:
            gcs_path: Path to file in GCS
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted file from GCS: {gcs_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {gcs_path}")
                return True  # Consider it successful if file doesn't exist
                
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error deleting file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def file_exists(self, gcs_path: str) -> bool:
        """
        Check if a file exists in Google Cloud Storage
        
        Args:
            gcs_path: Path to file in GCS
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            blob = self.bucket.blob(gcs_path)
            return blob.exists()
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error checking file existence: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
    
    def get_file_info(self, gcs_path: str) -> Optional[Dict]:
        """
        Get file information from Google Cloud Storage
        
        Args:
            gcs_path: Path to file in GCS
            
        Returns:
            Dictionary with file information, or None if failed
        """
        try:
            blob = self.bucket.blob(gcs_path)
            
            if not blob.exists():
                return None
            
            # Reload to get current metadata
            blob.reload()
            
            return {
                'name': blob.name,
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created,
                'updated': blob.updated,
                'etag': blob.etag,
                'md5_hash': blob.md5_hash,
                'crc32c': blob.crc32c
            }
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error getting file info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def list_files(self, prefix: str = "", max_results: int = 1000) -> List[Dict]:
        """
        List files in Google Cloud Storage bucket
        
        Args:
            prefix: Prefix to filter files
            max_results: Maximum number of results to return
            
        Returns:
            List of file information dictionaries
        """
        try:
            blobs = self.bucket.list_blobs(prefix=prefix, max_results=max_results)
            
            files = []
            for blob in blobs:
                files.append({
                    'name': blob.name,
                    'size': blob.size,
                    'content_type': blob.content_type,
                    'created': blob.time_created,
                    'updated': blob.updated
                })
            
            return files
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error listing files: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def generate_signed_url(self, gcs_path: str, expiration_hours: int = 1, 
                          method: str = 'GET', response_disposition: str = None) -> Optional[str]:
        """
        Generate a signed URL for accessing a file
        
        Args:
            gcs_path: Path to file in GCS
            expiration_hours: URL expiration time in hours
            method: HTTP method (GET, POST, etc.)
            response_disposition: Content-Disposition header value
            
        Returns:
            Signed URL string, or None if failed
        """
        try:
            blob = self.bucket.blob(gcs_path)
            
            if not blob.exists():
                logger.error(f"File not found for signed URL: {gcs_path}")
                return None
            
            expiration = datetime.utcnow() + timedelta(hours=expiration_hours)
            
            url = blob.generate_signed_url(
                expiration=expiration,
                method=method,
                response_disposition=response_disposition
            )
            
            logger.info(f"Generated signed URL for: {gcs_path}")
            return url
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error generating signed URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating signed URL: {e}")
            return None
    
    def copy_file(self, source_gcs_path: str, dest_gcs_path: str) -> bool:
        """
        Copy a file within Google Cloud Storage
        
        Args:
            source_gcs_path: Source file path in GCS
            dest_gcs_path: Destination file path in GCS
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_blob = self.bucket.blob(source_gcs_path)
            
            if not source_blob.exists():
                logger.error(f"Source file not found: {source_gcs_path}")
                return False
            
            dest_blob = self.bucket.blob(dest_gcs_path)
            dest_blob.rewrite(source_blob)
            
            logger.info(f"Copied file in GCS: {source_gcs_path} -> {dest_gcs_path}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error copying file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    def move_file(self, source_gcs_path: str, dest_gcs_path: str) -> bool:
        """
        Move a file within Google Cloud Storage
        
        Args:
            source_gcs_path: Source file path in GCS
            dest_gcs_path: Destination file path in GCS
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Copy file to new location
            if not self.copy_file(source_gcs_path, dest_gcs_path):
                return False
            
            # Delete original file
            if not self.delete_file(source_gcs_path):
                # If delete fails, try to clean up the copy
                self.delete_file(dest_gcs_path)
                return False
            
            logger.info(f"Moved file in GCS: {source_gcs_path} -> {dest_gcs_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False
    
    def calculate_file_hash(self, file_path: str, algorithm: str = 'sha256') -> Optional[str]:
        """
        Calculate hash of a local file
        
        Args:
            file_path: Path to local file
            algorithm: Hash algorithm ('sha256', 'md5', etc.)
            
        Returns:
            Hash string, or None if failed
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return None
    
    def calculate_content_hash(self, content: bytes, algorithm: str = 'sha256') -> str:
        """
        Calculate hash of content
        
        Args:
            content: Content as bytes
            algorithm: Hash algorithm ('sha256', 'md5', etc.)
            
        Returns:
            Hash string
        """
        try:
            hash_obj = hashlib.new(algorithm)
            hash_obj.update(content)
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating content hash: {e}")
            return ""
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
            
        Returns:
            Number of files cleaned up
        """
        try:
            temp_prefix = "temp/"
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            blobs = self.bucket.list_blobs(prefix=temp_prefix)
            
            deleted_count = 0
            for blob in blobs:
                if blob.time_created < cutoff_time:
                    try:
                        blob.delete()
                        deleted_count += 1
                        logger.info(f"Deleted old temp file: {blob.name}")
                    except Exception as e:
                        logger.error(f"Error deleting temp file {blob.name}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
            return 0
    
    def get_bucket_info(self) -> Dict:
        """
        Get information about the storage bucket
        
        Returns:
            Dictionary with bucket information
        """
        try:
            bucket = self.storage_client.get_bucket(self.bucket_name)
            
            return {
                'name': bucket.name,
                'location': bucket.location,
                'storage_class': bucket.storage_class,
                'created': bucket.time_created,
                'updated': bucket.updated,
                'metageneration': bucket.metageneration,
                'lifecycle_rules': len(bucket.lifecycle_rules) if bucket.lifecycle_rules else 0
            }
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error getting bucket info: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting bucket info: {e}")
            return {}
    
    def get_storage_usage(self) -> Dict:
        """
        Get storage usage statistics
        
        Returns:
            Dictionary with storage usage information
        """
        try:
            total_size = 0
            total_files = 0
            
            # Count files by type
            file_types = {}
            
            blobs = self.bucket.list_blobs()
            for blob in blobs:
                total_size += blob.size or 0
                total_files += 1
                
                # Count by content type
                content_type = blob.content_type or 'unknown'
                file_types[content_type] = file_types.get(content_type, 0) + 1
            
            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
                'file_types': file_types
            }
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error getting storage usage: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting storage usage: {e}")
            return {}