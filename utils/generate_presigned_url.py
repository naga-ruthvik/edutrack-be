import boto3
from django.conf import settings

from botocore.client import Config

def generate_presigned_url(object_key, expiration=3600):
    """Generates a temporary public URL for a private S3 object."""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version='s3v4'),
        endpoint_url=f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com"
    )
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                                                            'Key': object_key},
                                                    ExpiresIn=expiration)
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None
    return response
