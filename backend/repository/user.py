from sqlalchemy.orm import Session
from model.user import User

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_google_id(self, google_id: str):
        """Find a user by their Google ID"""
        return self.db.query(User).filter(User.google_id == google_id).first()

    def find_by_email(self, email: str):
        """Find a user by their email"""
        return self.db.query(User).filter(User.email == email).first()

    def create(self, user_data: dict):
        """Create a new user"""
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, update_data: dict):
        """Update user data"""
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user