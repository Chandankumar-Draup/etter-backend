import os
from typing import Optional
from common.common_utils import getCurrentEnvironment


class S3Config:
    VALID_ENVIRONMENTS = {'dev', 'qa', 'prod'}

    def __init__(self):
        self.aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region: str = os.getenv("AWS_REGION", "us-east-2")
        self.s3_bucket: str = os.getenv("S3_DOCUMENTS_BUCKET", "draup-etter")
        self.s3_endpoint_url: Optional[str] = os.getenv("S3_ENDPOINT_URL")

        # Get environment for S3 path prefixing
        self.environment: str = os.getenv("ENV") or getCurrentEnvironment()

        # Validate environment
        if self.environment not in self.VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment: {self.environment}. "
                f"Must be one of {self.VALID_ENVIRONMENTS}"
            )
        
        self.multipart_threshold_bytes: int = 100 * 1024 * 1024
        self.multipart_part_size: int = 5 * 1024 * 1024
        self.max_single_upload_size: int = 10 * 1024 * 1024
        self.max_multipart_upload_size: int = 5 * 1024 * 1024 * 1024
        
        self.presigned_url_ttl_seconds: int = 300
        
        self.sse_algorithm: str = "AES256"
        
        self.connect_timeout_seconds: int = 10
        self.read_timeout_seconds: int = 300
        self.max_retries: int = 3


s3_config = S3Config()


class Constants:
    AUDIT_ACTION_DOCUMENT_UPLOADED = "DocumentUploaded"
    AUDIT_ACTION_DOCUMENT_DELETED = "DocumentDeleted"
    AUDIT_ACTION_DOCUMENT_QUARANTINED = "DocumentQuarantined"
    AUDIT_ACTION_DOCUMENT_APPROVED = "DocumentApproved"
    AUDIT_ACTION_UPLOAD_ABORTED = "UploadAborted"
    AUDIT_ACTION_PART_UPLOADED = "PartUploaded"
    
    IDEMPOTENCY_KEY_TTL_HOURS = 24

