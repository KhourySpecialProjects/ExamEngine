from backend.src.core.config import get_settings
from dotenv import load_dotenv


load_dotenv()

settings = get_settings()


def test_get_settings():
    assert settings is not None
    assert settings.environment in ["development", "production", "testing"]
    assert settings.database_url is not None
    assert settings.aws_access_key_id is not None
    assert settings.aws_secret_access_key is not None
    assert settings.secret_key is not None
    assert settings.algorithm == "HS256"
    assert settings.access_token_expire_minutes == 1440
    assert settings.frontend_url == "http://localhost:3000"
    assert settings.aws_region is not None
    assert settings.aws_s3_bucket is not None
    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 10
