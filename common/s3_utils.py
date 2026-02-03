import os
import boto3
import mimetypes
from botocore.exceptions import ClientError
from common.logger import logger
from api.s3.config import s3_config
from api.s3.infra.s3.s3_management_service import S3ManagementService

AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_FILE_DL_EXPIRY = 604800


def generate_presigned_s3_get(bucket_name: str, key: str, expiration: int) -> str:
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise


def set_lifecycle(s3, bucket_name: str, id: str, prefix: str, status: str, expiration: int):
    try:
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration={
                'Rules': [{
                    'Id': id,
                    'Status': status,
                    'Filter': {'Prefix': prefix},
                    'Expiration': {'Days': expiration // (24 * 60 * 60)}
                }]
            }
        )
    except Exception as e:
        logger.error(f"Error setting lifecycle: {e}")


def get_expiry():
    return 7


def get_public_url(bucket_name: str, key: str, region: str = AWS_REGION) -> str:
    return f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"


def get_s3_environment() -> str:
    return s3_config.environment


def get_s3_bucket_name() -> str:
    return s3_config.s3_bucket

def upload_to_s3_with_config(
    file,
    key,
    is_public=False,
    to_get_url=False,
    old_report_key=None,
    expiration_days=7,
    bucket_name=None,
):
    bucket_name = bucket_name or get_s3_bucket_name()
    try:
        size = os.fstat(file.fileno()).st_size
    except Exception as e:
        logger.exception(e)
        file.seek(0, os.SEEK_END)
        size = file.tell()
    finally:
        try:
            file.seek(0)
        except Exception:
            pass

    service = S3ManagementService()
    service.bucket = bucket_name

    content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    metadata = {'Content-Type': content_type}

    response = service.put_single(
        key=key,
        fileobj=file,
        metadata=metadata,
        content_type=content_type
    )

    if response:
        verification = service.head_object(key)
        try:
            file.seek(0)
        except Exception:
            pass
        if verification.content_length == size and verification.etag == response.etag:
            if is_public:
                public_url = get_public_url(bucket_name, key)
                return public_url
            if old_report_key:
                set_lifecycle(s3=service.client, bucket_name=bucket_name, id=old_report_key, prefix=old_report_key, status='Enabled',
                              expiration=get_expiry())
            if to_get_url:
                set_expiration = (expiration_days * 24 * 60 * 60 if expiration_days != 7 else S3_FILE_DL_EXPIRY)
                res_url = generate_presigned_s3_get(bucket_name, key, set_expiration)
                return res_url

            return True
        return False
    return False

