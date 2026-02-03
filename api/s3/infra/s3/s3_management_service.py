import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Dict, Optional, BinaryIO, List
from dataclasses import dataclass
from datetime import datetime
import logging

from api.s3.config import s3_config
from models.s3 import UploadModeV2
logger = logging.getLogger(__name__)


@dataclass
class S3PutResult:
    etag: str
    version_id: Optional[str]
    sse_algorithm: Optional[str]
    bucket: str
    key: str


@dataclass
class S3Verification:
    content_length: int
    content_type: Optional[str]
    sse_algorithm: Optional[str]
    etag: str
    last_modified: datetime
    tags: Dict[str, str]


@dataclass
class S3MultipartUpload:
    upload_id: str
    bucket: str
    key: str


@dataclass
class S3PartResult:
    part_number: int
    etag: str


class S3ManagementService:
    def __init__(self):
        boto_config = Config(
            connect_timeout=s3_config.connect_timeout_seconds,
            read_timeout=s3_config.read_timeout_seconds,
            retries={'max_attempts': s3_config.max_retries, 'mode': 'adaptive'}
        )
        
        # self.client = boto3.client(
        #     's3',
        #     aws_access_key_id=s3_config.aws_access_key_id,
        #     aws_secret_access_key=s3_config.aws_secret_access_key,
        #     region_name=s3_config.aws_region,
        #     # endpoint_url=s3_config.s3_endpoint_url,
        #     config=boto_config
        # )
        self.client = boto3.client('s3', config=boto_config)
        
        self.bucket = s3_config.s3_bucket
        self.sse_algorithm = s3_config.sse_algorithm

    def put_single(
        self,
        key: str,
        fileobj: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> S3PutResult:
        extra_args = {
            'ServerSideEncryption': self.sse_algorithm
        }
        
        if metadata:
            extra_args['Metadata'] = metadata
        
        if content_type:
            extra_args['ContentType'] = content_type
        
        if tags:
            tag_string = '&'.join([f"{k}={v}" for k, v in tags.items()])
            extra_args['Tagging'] = tag_string
        
        try:
            response = self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=fileobj,
                **extra_args
            )
            
            logger.info(f"Successfully uploaded object to s3://{self.bucket}/{key}")
            
            return S3PutResult(
                etag=response['ETag'].strip('"'),
                version_id=response.get('VersionId'),
                sse_algorithm=response.get('ServerSideEncryption'),
                bucket=self.bucket,
                key=key
            )
        except ClientError as e:
            logger.error(f"Failed to upload object to S3: {e}")
            raise

    def create_multipart(
        self,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> S3MultipartUpload:
        extra_args = {
            'ServerSideEncryption': self.sse_algorithm
        }
        
        if metadata:
            extra_args['Metadata'] = metadata
        
        if content_type:
            extra_args['ContentType'] = content_type
        
        if tags:
            tag_string = '&'.join([f"{k}={v}" for k, v in tags.items()])
            extra_args['Tagging'] = tag_string
        
        try:
            response = self.client.create_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                **extra_args
            )
            
            upload_id = response['UploadId']
            logger.info(f"Created multipart upload for s3://{self.bucket}/{key} with upload_id={upload_id}")
            
            return S3MultipartUpload(
                upload_id=upload_id,
                bucket=self.bucket,
                key=key
            )
        except ClientError as e:
            logger.error(f"Failed to create multipart upload: {e}")
            raise

    def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: BinaryIO
    ) -> S3PartResult:
        try:
            response = self.client.upload_part(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=data
            )
            
            etag = response['ETag'].strip('"')
            logger.debug(f"Uploaded part {part_number} for upload_id={upload_id}, etag={etag}")
            
            return S3PartResult(
                part_number=part_number,
                etag=etag
            )
        except ClientError as e:
            logger.error(f"Failed to upload part {part_number}: {e}")
            raise

    def complete_multipart(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, any]]
    ) -> S3PutResult:
        try:
            response = self.client.complete_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            logger.info(f"Completed multipart upload for s3://{self.bucket}/{key}, upload_id={upload_id}")
            
            return S3PutResult(
                etag=response['ETag'].strip('"'),
                version_id=response.get('VersionId'),
                sse_algorithm=response.get('ServerSideEncryption'),
                bucket=self.bucket,
                key=key
            )
        except ClientError as e:
            logger.error(f"Failed to complete multipart upload: {e}")
            raise

    def abort_multipart(self, key: str, upload_id: str) -> None:
        try:
            self.client.abort_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id
            )
            logger.info(f"Aborted multipart upload for s3://{self.bucket}/{key}, upload_id={upload_id}")
        except ClientError as e:
            logger.error(f"Failed to abort multipart upload: {e}")
            raise

    def head_object(self, key: str) -> S3Verification:
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=key
            )
            
            tags = self.get_tags(key)
            
            return S3Verification(
                content_length=response['ContentLength'],
                content_type=response.get('ContentType'),
                sse_algorithm=response.get('ServerSideEncryption'),
                etag=response['ETag'].strip('"'),
                last_modified=response['LastModified'],
                tags=tags
            )
        except ClientError as e:
            logger.error(f"Failed to head object: {e}")
            raise

    def get_tags(self, key: str) -> Dict[str, str]:
        try:
            response = self.client.get_object_tagging(
                Bucket=self.bucket,
                Key=key
            )
            
            tags = {tag['Key']: tag['Value'] for tag in response.get('TagSet', [])}
            return tags
        except ClientError as e:
            logger.error(f"Failed to get tags: {e}")
            raise

    def put_tags(self, key: str, tags: Dict[str, str]) -> None:
        try:
            tag_set = [{'Key': k, 'Value': v} for k, v in tags.items()]
            self.client.put_object_tagging(
                Bucket=self.bucket,
                Key=key,
                Tagging={'TagSet': tag_set}
            )
            logger.debug(f"Updated tags for s3://{self.bucket}/{key}")
        except ClientError as e:
            logger.error(f"Failed to put tags: {e}")
            raise

    def delete_object(self, key: str) -> None:
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            logger.info(f"Deleted object s3://{self.bucket}/{key}")
        except ClientError as e:
            logger.error(f"Failed to delete object: {e}")
            raise

    def generate_presigned_get_url(
        self,
        key: str,
        ttl_seconds: Optional[int] = None
    ) -> str:
        if ttl_seconds is None:
            ttl_seconds = s3_config.presigned_url_ttl_seconds
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key
                },
                ExpiresIn=ttl_seconds
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def get_object_stream(self, key: str):
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=key
            )
            return response['Body']
        except ClientError as e:
            logger.error(f"Failed to get object from S3: {e}")
            raise

    def build_key(
        self,
        tenant_id: str,
        mode: 'UploadModeV2',
        folder_path: Optional[str] = None,
        role: Optional[str] = None,
        original_filename: str = None
    ) -> str:
        """Build S3 key based on upload mode with environment prefix."""
        from models.s3 import UploadModeV2
        from api.s3.config import s3_config

        environment = s3_config.environment

        if mode == UploadModeV2.FILESYSTEM:
            if not folder_path:
                raise ValueError("folder_path required for filesystem mode")
            folder_path = self._normalize_path(folder_path)
            return f"{environment}/{tenant_id}/fs/{folder_path}/{original_filename}"
        else:  # ROLE_BASED
            if not role:
                raise ValueError("role required for role_based mode")
            return f"{environment}/{tenant_id}/roles/{role}/{original_filename}"

    def _normalize_path(self, path: str) -> str:
        """Normalize folder path."""
        path = path.strip('/')
        if '..' in path or path.startswith('/'):
            raise ValueError("Invalid path")
        path = '/'.join(filter(None, path.split('/')))
        if len(path) > 500:
            raise ValueError("Path too long")
        return path

