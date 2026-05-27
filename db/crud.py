from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from db.models import Base, People
import os
from dotenv import load_dotenv

load_dotenv()


def init_db():

    # Fetching DB URL from env variables
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("DATABASE_URL is not set in .env file")

    # Create SQLAlchemy engine
    engine = create_engine(db_url, echo=False)

    # Create all tables if they don't exist
    Base.metadata.create_all(engine)

    # Initialize SQL session factory
    sql_session = sessionmaker(bind=engine)

    return sql_session


def insert_people(session: Session, people: People) -> bool:
    """
    Insert a new People record into DB
    """

    try:
        session.add(people)
        session.commit()

        print(f"Inserted person with ID: {people.id}")
        return True

    except Exception as e:
        session.rollback()
        print(f"Error inserting person: {e}")
        return False


def delete_people(person_id: int, session: Session) -> bool:
    """
    Delete a person using ID
    """

    try:
        person = session.query(People).filter(
            People.id == person_id
        ).first()

        if not person:
            print(f"No person found with ID: {person_id}")
            return False

        session.delete(person)
        session.commit()

        print(f"Deleted person with ID: {person_id}")
        return True

    except Exception as e:
        session.rollback()
        print(f"Error deleting person: {e}")
        return False


def fetch_people_metadata(
    people_ids: list[int],
    session: Session
) -> list[dict]:
    """
    Fetch metadata for all IDs present in people_ids
    using raw SQL query executed through SQLAlchemy session
    """

    try:

        if not people_ids:
            return []

        result = session.query(People).filter(People.id.in_(people_ids)).all()

        # Convert rows to list of dictionaries
        people_data = [
            {
                "id": row.id,
                "name": row.name,
                "diet_pref": row.diet_pref,
                "drinks_alcohol": bool(row.drinks_alcohol)
            }
            for row in result
        ]

        return people_data

    except Exception as e:
        print(f"Error fetching people metadata: {e}")
        return []