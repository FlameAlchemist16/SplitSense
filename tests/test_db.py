import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.crud import init_db, insert_people, fetch_people_metadata
from db.models import People

SessionFactory = init_db()
session = SessionFactory()
print("Database initialized successfully")
print(f"Session: {session}")

test_user1 = People(name = "user1", diet_pref = "veg", drinks_alcohol = False, phone = "1234567890", email = "dummy1@test.org")
test_user2 = People(name = "user2", diet_pref = "non_veg", drinks_alcohol = True, phone = "1357902468", email = "dummy2@test.org")
test_user3 = People(name = "user3", diet_pref = "veg", drinks_alcohol = True, phone = "9876543210", email = "dummy3@test.org")

insert_people(session=session, people=test_user1)
insert_people(session=session, people=test_user2)
insert_people(session=session, people=test_user3)

data1 = fetch_people_metadata(people_ids=[1,2,3], session=session)
print(data1)

session.close()