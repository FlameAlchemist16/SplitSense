from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Float, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class People(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)
    diet_pref = Column(Enum("veg","non_veg"), nullable=False)
    drinks_alcohol = Column(Boolean, default=False, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

class Groups(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)
    members = Column(list, nullable=False)
    created_at = Column(DateTime, nullable=False)

class Bills(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    image_url = Column(String, nullable=False)
    total = Column(Float, nullable=False)
    currency = Column(String, default="INR", nullable=False)
    paid_by_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    raw_json = Column(String, nullable=False)

class Splits(Base):
    __tablename__ = "splits"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    amount_owed = Column(Float, nullable=False)