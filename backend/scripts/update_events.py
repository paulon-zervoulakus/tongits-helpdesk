from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db
from model.events import Happenings

def update_event(db: Session, event_id: int, **kwargs):
    """
    Update an existing event in the Happenings table.
    
    Args:
        db (Session): Database session
        event_id (int): ID of the event to update
        **kwargs: Fields to update (title, description, date_of_event, etc.)
    """
    event = db.query(Happenings).filter(Happenings.id == event_id).first()
    if not event:
        print(f"Event with ID {event_id} not found.")
        return None
    
    # Update fields
    for key, value in kwargs.items():
        if hasattr(event, key):
            setattr(event, key, value)
    
    try:
        db.commit()
        print(f"Successfully updated event: {event.title}")
        return event
    except Exception as e:
        db.rollback()
        print(f"Error updating event: {str(e)}")
        return None

def main():
    # Get database session
    db = next(get_db())
    
    try:
        # Example: Update an event
        event_updates = {
            "event_id": 1,  # Replace with the actual event ID
            "updates": {
                "title": "Updated Tongits Tournament",
                "description": "Join us for an exciting evening of Tongits!",
                "date_of_event": datetime(2025, 10, 1, 18, 0),  # Year, Month, Day, Hour, Minute
                "organizer": "John Doe",
                "contact_info": "john.doe@example.com"
            }
        }
        
        # Print current event details
        event = db.query(Happenings).filter(Happenings.id == event_updates["event_id"]).first()
        if event:
            print("\nCurrent event details:")
            print(event.to_dict())
        
        # Update the event
        updated_event = update_event(db, event_updates["event_id"], **event_updates["updates"])
        
        if updated_event:
            print("\nUpdated event details:")
            print(updated_event.to_dict())
    
    finally:
        db.close()

if __name__ == "__main__":
    # Example usage:
    # 1. Single event update
    main()
    
    # 2. Multiple event updates example:
    """
    db = next(get_db())
    try:
        # Update multiple events
        updates = [
            {
                "event_id": 1,
                "updates": {
                    "title": "Morning Tongits Session",
                    "date_of_event": datetime(2025, 10, 1, 10, 0)
                }
            },
            {
                "event_id": 2,
                "updates": {
                    "title": "Evening Tournament",
                    "date_of_event": datetime(2025, 10, 1, 18, 0)
                }
            }
        ]
        
        for update in updates:
            update_event(db, update["event_id"], **update["updates"])
    
    finally:
        db.close()
    """