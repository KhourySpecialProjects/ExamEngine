import os

from db import Base
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def reset_database():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    engine = create_engine(db_url, echo=True)

    print("⚠️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

    print("✅ Creating all tables with new schema...")
    Base.metadata.create_all(bind=engine)

    print("✅ Database reset complete!")


if __name__ == "__main__":
    reset_database()
