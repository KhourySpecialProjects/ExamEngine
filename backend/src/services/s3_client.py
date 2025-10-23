import boto3
import os
from dotenv import load_dotenv


load_dotenv()

s3_client = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION", "us-east-1")
)

def get_client():
    return s3_client