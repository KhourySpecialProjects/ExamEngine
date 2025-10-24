from dotenv import load_dotenv
load_dotenv() 
import os
from .s3 import S3

storage_service = S3(
    bucket_name=os.getenv("AWS_S3_BUCKET", "exam-engine-csvs"),
    region=os.getenv("AWS_REGION", "us-east-1")
)
