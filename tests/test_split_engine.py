import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.tools.split_engine import calculate_split
from db.crud import init_db, fetch_people_metadata

SessionFactory = init_db()
session = SessionFactory()
print("Database initialized successfully")
print(f"Session: {session}")

bill_data = {
    "item_details": [
        {"item": "Paneer Tikka", "price": 320.0, "category": "veg", "quantity": 1, "confidence": 0.95},
        {"item": "Chicken Biryani", "price": 450.0, "category": "non_veg", "quantity": 1, "confidence": 0.95},
        {"item": "Beer x4", "price": 600.0, "category": "alcohol", "quantity": 4, "confidence": 0.95},
        {"item": "Bread Basket", "price": 150.0, "category": "shared", "quantity": 1, "confidence": 0.95},
        {"item": "CGST 2.5%", "price": 38.0, "category": "tax", "quantity": None, "confidence": 0.95},
    ]
}

people = fetch_people_metadata(people_ids=[1,2,3], session=session)
print(people)

result = calculate_split(bill_data, people)

print("=== SPLITS ===")
for split in result["splits"]:
    print(split)

print("\n=== WARNINGS ===")
for warning in result["warnings"]:
    print(warning)