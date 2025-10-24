import os

from dotenv import load_dotenv

from .s3 import S3


load_dotenv()


storage_service = S3(
    bucket_name=os.getenv("AWS_S3_BUCKET", "exam-engine-csvs"),
    region=os.getenv("AWS_REGION", "us-east-1"),
)
