"""
AWS S3 Client for Image Storage
Handles upload and presigned URL generation
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Client:
    """Client for interacting with AWS S3 for image storage."""
    
    def __init__(self):
        """Initialize S3 client."""
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("S3_BUCKET")
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET environment variable is required")
        
        self.s3_client = boto3.client(
            service_name="s3",
            region_name=self.region
        )
        
        self.presigned_url_expiry = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))
        
        logger.info(f"Initialized S3 client with bucket: {self.bucket_name}")
    
    def check_health(self) -> bool:
        """Check if S3 bucket is accessible."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception as e:
            logger.error(f"S3 health check failed: {str(e)}")
            raise
    
    async def upload_image(
        self,
        image_data: bytes,
        image_id: str,
        metadata: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Upload an image to S3.
        
        Args:
            image_data: Image bytes
            image_id: Unique identifier for the image
            metadata: Optional metadata to attach to the object
            
        Returns:
            Dictionary with upload result:
            {
                "key": str,
                "bucket": str,
                "size": int
            }
        """
        try:
            # Generate S3 key with date-based prefix
            date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
            s3_key = f"images/{date_prefix}/{image_id}.png"
            
            # Prepare metadata
            s3_metadata = metadata or {}
            s3_metadata["image_id"] = image_id
            
            # Upload to S3
            logger.debug(f"Uploading image to s3://{self.bucket_name}/{s3_key}")
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_data,
                ContentType="image/png",
                Metadata=s3_metadata,
                ServerSideEncryption="AES256"  # Enable encryption at rest
            )
            
            logger.info(f"Successfully uploaded image to S3: {s3_key}")
            
            return {
                "key": s3_key,
                "bucket": self.bucket_name,
                "size": len(image_data)
            }
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"S3 upload error: {error_code} - {error_message}")
            raise Exception(f"Failed to upload image to S3: {error_message}")
        
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            raise
    
    async def generate_presigned_url(
        self,
        s3_key: str,
        expiry_seconds: int = None
    ) -> str:
        """
        Generate a presigned URL for accessing an image.
        
        Args:
            s3_key: S3 object key
            expiry_seconds: URL expiry time in seconds (default from env)
            
        Returns:
            Presigned URL string
        """
        try:
            expiry = expiry_seconds or self.presigned_url_expiry
            
            logger.debug(f"Generating presigned URL for {s3_key} (expiry: {expiry}s)")
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiry
            )
            
            logger.info(f"Generated presigned URL for {s3_key}")
            return url
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Error generating presigned URL: {error_code} - {error_message}")
            raise Exception(f"Failed to generate presigned URL: {error_message}")
        
        except Exception as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise
    
    async def delete_image(self, s3_key: str) -> bool:
        """
        Delete an image from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if successful
        """
        try:
            logger.debug(f"Deleting image from S3: {s3_key}")
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Successfully deleted image: {s3_key}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting image: {str(e)}")
            raise
    
    async def list_images(
        self,
        prefix: str = "images/",
        max_keys: int = 100
    ) -> list:
        """
        List images in S3 bucket.
        
        Args:
            prefix: S3 key prefix to filter
            max_keys: Maximum number of keys to return
            
        Returns:
            List of S3 object metadata
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = response.get('Contents', [])
            
            return [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat()
                }
                for obj in objects
            ]
        
        except Exception as e:
            logger.error(f"Error listing images: {str(e)}")
            raise
