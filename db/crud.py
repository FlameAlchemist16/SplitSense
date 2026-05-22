from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base
import os
from dotenv import load_dotenv

load_dotenv()

def init_db():

    # Fetching DB URL from env variables
    db_url = os.getenv("DATABASE_URL")

    # create sqlalchemy engine
    engine = create_engine(db_url)

    # create all tables if they don't exits
    Base.metadata.create_all(engine)

    # initializing sql session
    sql_session = sessionmaker(bind = engine)
    return sql_session