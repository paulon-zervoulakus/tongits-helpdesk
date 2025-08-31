from requests import Session
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from sqlalchemy.ext.declarative import declarative_base


# Database
DATABASE_URL = "sqlite:///./bookings.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that creates a new SQLAlchemy session for each request
    and closes it when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)