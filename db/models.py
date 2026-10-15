from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship


def utc_now():
    return datetime.now(timezone.utc)


Base = declarative_base()


class People(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)
    diet_pref = Column(Enum("veg", "non_veg", name="diet_pref"), nullable=False)
    drinks_alcohol = Column(Boolean, default=False, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    splits = relationship("Splits", back_populates="person")
    bills_paid = relationship("Bills", back_populates="paid_by")


class Groups(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    members = relationship("GroupMembers", back_populates="group")
    bills = relationship("Bills", back_populates="group")


class GroupMembers(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "person_id", name="uq_group_person"),)

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)

    group = relationship("Groups", back_populates="members")
    person = relationship("People")


class Bills(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    image_url = Column(String, nullable=False)
    total = Column(Float, nullable=False)
    currency = Column(String, default="INR", nullable=False)
    paid_by_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    date = Column(DateTime, nullable=False, default=utc_now)
    raw_json = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)

    group = relationship("Groups", back_populates="bills")
    paid_by = relationship("People", back_populates="bills_paid")
    splits = relationship("Splits", back_populates="bill")


class Splits(Base):
    __tablename__ = "splits"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    amount_owed = Column(Float, nullable=False)

    bill = relationship("Bills", back_populates="splits")
    person = relationship("People", back_populates="splits")


class Settlements(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    from_person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    to_person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    note = Column(String, nullable=True)

    from_person = relationship("People", foreign_keys=[from_person_id])
    to_person = relationship("People", foreign_keys=[to_person_id])
