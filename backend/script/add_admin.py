import os
import sys
from pathlib import Path
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.schemas.db import Users
from src.utils.password import get_password_hash


load_dotenv()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "theadmin@northeastern.edu")
ADMIN_NAME = "Administator"


def add_admin():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    engine = create_engine(db_url, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # noqa: N806
    db = SessionLocal()

    uuid = uuid4()

    admin_user = Users(
        user_id=uuid,
        name=ADMIN_NAME,
        email=ADMIN_EMAIL,
        password_hash=get_password_hash(ADMIN_PASSWORD),
        role="admin",
        status="Approved",
    )
    db = SessionLocal()
    db.add(admin_user)
    db.commit()
    db.close()


if __name__ == "__main__":
    add_admin()
