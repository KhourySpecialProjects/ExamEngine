from dotenv import load_dotenv

from src.core.config import get_settings

from .s3 import S3


load_dotenv()
setting = get_settings()

storage = S3(
    bucket_name=setting.aws_s3_bucket,
    region=setting.aws_region,
)
