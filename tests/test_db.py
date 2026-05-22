import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.crud import init_db

SessionFactory = init_db()
session = SessionFactory()
print("Database initialized successfully")
print(f"Session: {session}")
session.close()