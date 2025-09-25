from database import SessionLocal
from model.events import Happenings
from datetime import datetime
# Create a new session
db = SessionLocal()

# create datetime object
event_date = datetime(2025, 9, 30, 19, 0, 0)  # yyyy, mm, dd, HH, MM, SS

# insert a new happening
new_event = Happenings(
    title="Community Game Night",
    description="A fun night of Tongits and other card games.",
    picture="event1.png",
    date_of_event=event_date,
    organizer="Paulon Zervoulakus",
    contact_info="paulon.zervoulakus@gmail.com",
)

# Add and commit
db.add(new_event)
db.commit()
db.refresh(new_event)  # refresh to get the generated ID

print("Inserted Happening:", new_event.to_dict())
