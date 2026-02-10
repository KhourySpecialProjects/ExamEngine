import boto3
from botocore.exceptions import ClientError

from .interface import IStorage


class S3(IStorage):
    """
    AWS S3 storage implementation.

    Supports both real AWS S3 and LocalStack for local development.
    When endpoint_url is provided, it will use LocalStack.
    When endpoint_url is None, it uses real AWS S3.
    """

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ) -> None:
        super().__init__()
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url

        self.client = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=endpoint_url,  # None for real AWS, URL for LocalStack
        )

    async def upload_file(
        self, file_content: bytes, key: str, content_type: str = "text/csv"
    ) -> tuple[str | None, str | None]:
        """Upload file to S3"""
        try:
            # Use put_object instead of upload_fileobj for better async compatibility
            # The boto3 client operations are synchronous but the await gives other tasks a chance to run
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type,
            )
            return None, key
        except ClientError as e:
            return f"S3 upload error: {str(e)}", None
        except Exception as e:
            return f"Upload error: {str(e)}", None

    def download_file(self, key: str) -> bytes | None:
        """Download file from S3"""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            print(f"S3 download error: {e}")
            return None
        except Exception as e:
            print(f"Download error: {e}")
            return None

    def delete_file(self, key: str) -> bool:
        """Delete single file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            print(f"S3 delete error: {e}")
            return False

    def delete_directory(self, prefix: str) -> bool:
        """Delete all files with given prefix from S3"""
        try:
            # Ensure prefix ends with /
            if prefix and not prefix.endswith("/"):
                prefix += "/"

            # List all objects with prefix
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )

            if "Contents" not in response:
                return True  # No files to delete

            # Delete all objects
            objects_to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]

            self.client.delete_objects(
                Bucket=self.bucket_name, Delete={"Objects": objects_to_delete}
            )

            return True
        except ClientError as e:
            print(f"S3 delete directory error: {e}")
            return False

    def file_exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
