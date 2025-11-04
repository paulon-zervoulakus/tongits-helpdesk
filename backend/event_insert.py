from database import SessionLocal
from model.events import Happenings
from datetime import datetime
# Create a new session
db = SessionLocal()

# db.query(Happenings).delete()
# db.commit()
# create datetime object
event_date = datetime(2025, 10, 15, 19, 0, 0)  # yyyy, mm, dd, HH, MM, SS

# insert a new happening
new_event = Happenings(
    title="Dota2 Finals day 2 (Trashtalk ON)",
    description="The International 2025 (also commonly called TI 2025 or TI 14) is the fourteenth annual edition of The International which will take place in Hamburg, Germany.",
    picture="event1.png",
    date_of_event=event_date,
    organizer="Roshan (the Immortal)",
    contact_info="ros@gmail.com",
)

# Add and commit
db.add(new_event)
db.commit()
db.refresh(new_event)  # refresh to get the generated ID

print("Inserted Happening:", new_event.to_dict())
