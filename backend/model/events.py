from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Happenings(Base):
    __tablename__ = "happenings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    description = Column(String)
    event_outcome = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    date_of_event = Column(DateTime(timezone=True), nullable=True)
    organizer = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    participants = relationship("Participant", back_populates="happening", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "event_outcome": self.event_outcome,
            "picture": self.picture,
            "date_of_event": self.date_of_event,
            "organizer": self.organizer,
            "contact_info": self.contact_info
        }


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("happenings.id"), index=True)
    fullname = Column(String, nullable=True)
    email = Column(String, nullable=True)
    nickname = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    happening = relationship("Happenings", back_populates="participants")

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "fullname": self.fullname,
            "email": self.email,
            "nickname": self.nickname,
            "availability": self.availability
        }
