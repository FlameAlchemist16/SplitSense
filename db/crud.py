import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, Bills, GroupMembers, Groups, People, Settlements, Splits

load_dotenv()


def init_db(db_url: str | None = None):
    db_url = db_url or os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("DATABASE_URL is not set in .env file")

    engine_kwargs = {"echo": False}
    if db_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(db_url, **engine_kwargs)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def insert_people(session: Session, people: People, *, quiet: bool = False) -> bool:
    try:
        session.add(people)
        session.commit()
        if not quiet:
            print(f"Inserted person with ID: {people.id}")
        return True
    except Exception as e:
        session.rollback()
        print(f"Error inserting person: {e}")
        return False


def delete_people(person_id: int, session: Session) -> bool:
    try:
        person = session.query(People).filter(People.id == person_id).first()
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


def fetch_people_metadata(people_ids: list[int], session: Session) -> list[dict]:
    try:
        if not people_ids:
            return []
        result = session.query(People).filter(People.id.in_(people_ids)).all()
        by_id = {row.id: row for row in result}
        people_data = []
        for pid in people_ids:
            row = by_id.get(pid)
            if not row:
                continue
            people_data.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "diet_pref": row.diet_pref,
                    "drinks_alcohol": bool(row.drinks_alcohol),
                }
            )
        return people_data
    except Exception as e:
        print(f"Error fetching people metadata: {e}")
        return []


def list_people(session: Session) -> list[People]:
    return session.query(People).order_by(People.id).all()


def get_people_by_names(session: Session, names: list[str]) -> list[People]:
    found = []
    missing = []
    for name in names:
        matches = (
            session.query(People)
            .filter(People.name.ilike(name))
            .order_by(People.id)
            .all()
        )
        if not matches:
            missing.append(name)
        else:
            found.append(matches[0])
    if missing:
        raise ValueError(
            "Unknown people: "
            + ", ".join(missing)
            + ". Add them first with: python -m agent.core people add --name NAME --diet veg|non_veg"
        )
    return found


def people_to_split_dicts(people: list[People]) -> list[dict]:
    return [
        {
            "id": person.id,
            "name": person.name,
            "diet_pref": person.diet_pref,
            "drinks_alcohol": bool(person.drinks_alcohol),
        }
        for person in people
    ]


def list_groups(session: Session) -> list[dict]:
    groups = session.query(Groups).order_by(Groups.name).all()
    result = []
    for group in groups:
        members = (
            session.query(People)
            .join(GroupMembers, GroupMembers.person_id == People.id)
            .filter(GroupMembers.group_id == group.id)
            .order_by(People.name)
            .all()
        )
        result.append(
            {
                "id": group.id,
                "name": group.name,
                "member_ids": [m.id for m in members],
                "member_names": [m.name for m in members],
            }
        )
    return result


def get_group_member_ids(session: Session, group_name: str) -> list[int]:
    group = session.query(Groups).filter(Groups.name.ilike(group_name)).first()
    if not group:
        raise ValueError(f"Group not found: {group_name}")
    rows = session.query(GroupMembers.person_id).filter(GroupMembers.group_id == group.id).all()
    return [row[0] for row in rows]


def get_or_create_group(session: Session, name: str, member_ids: list[int]) -> Groups:
    group = session.query(Groups).filter(Groups.name == name).first()
    if not group:
        group = Groups(name=name, created_at=datetime.now(timezone.utc))
        session.add(group)
        session.flush()
    existing = {
        row.person_id
        for row in session.query(GroupMembers).filter(GroupMembers.group_id == group.id)
    }
    for person_id in member_ids:
        if person_id not in existing:
            session.add(GroupMembers(group_id=group.id, person_id=person_id))
    session.commit()
    session.refresh(group)
    return group


def insert_bill(
    session: Session,
    *,
    image_url: str,
    total: float,
    paid_by_id: int,
    raw_json: str,
    currency: str = "INR",
    group_id: int | None = None,
    notes: str | None = None,
    date: datetime | None = None,
) -> Bills:
    bill = Bills(
        group_id=group_id,
        image_url=image_url,
        total=total,
        currency=currency,
        paid_by_id=paid_by_id,
        date=date or datetime.now(timezone.utc),
        raw_json=raw_json,
        notes=notes,
    )
    session.add(bill)
    session.commit()
    session.refresh(bill)
    return bill


def insert_splits(session: Session, bill_id: int, splits: list[dict]) -> list[Splits]:
    rows = []
    for split in splits:
        row = Splits(
            bill_id=bill_id,
            person_id=split["id"],
            amount_owed=split["amount_owed"],
        )
        session.add(row)
        rows.append(row)
    session.commit()
    return rows


def list_bills(session: Session) -> list[Bills]:
    return session.query(Bills).order_by(Bills.date.desc(), Bills.id.desc()).all()


def insert_settlement(
    session: Session,
    from_person_id: int,
    to_person_id: int,
    amount: float,
    note: str | None = None,
) -> Settlements:
    if amount <= 0:
        raise ValueError("Settlement amount must be greater than 0")
    if from_person_id == to_person_id:
        raise ValueError("Cannot settle with the same person")
    row = Settlements(
        from_person_id=from_person_id,
        to_person_id=to_person_id,
        amount=amount,
        created_at=datetime.now(timezone.utc),
        note=note,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def compute_nets(session: Session) -> list[dict]:
    people = list_people(session)
    nets = {person.id: 0.0 for person in people}
    names = {person.id: person.name for person in people}

    for bill in session.query(Bills).all():
        nets[bill.paid_by_id] = nets.get(bill.paid_by_id, 0.0) + (bill.total or 0)
        for split in session.query(Splits).filter(Splits.bill_id == bill.id):
            nets[split.person_id] = nets.get(split.person_id, 0.0) - (split.amount_owed or 0)

    for settlement in session.query(Settlements).all():
        nets[settlement.from_person_id] = nets.get(settlement.from_person_id, 0.0) + (
            settlement.amount or 0
        )
        nets[settlement.to_person_id] = nets.get(settlement.to_person_id, 0.0) - (
            settlement.amount or 0
        )

    return [
        {"id": person_id, "name": names.get(person_id, str(person_id)), "net": round(net, 2)}
        for person_id, net in nets.items()
    ]


def compute_nets_with_pending_bill(
    session: Session,
    *,
    paid_by_id: int,
    total: float,
    splits: list[dict],
) -> list[dict]:
    """Preview group nets if this bill were committed (does not write to DB)."""
    nets = {row["id"]: dict(row) for row in compute_nets(session)}
    for person in list_people(session):
        if person.id not in nets:
            nets[person.id] = {
                "id": person.id,
                "name": person.name,
                "net": 0.0,
            }

    nets[paid_by_id]["net"] = round(nets[paid_by_id]["net"] + float(total), 2)
    for split in splits:
        person_id = split["id"]
        if person_id not in nets:
            person = session.query(People).filter(People.id == person_id).first()
            nets[person_id] = {
                "id": person_id,
                "name": person.name if person else str(person_id),
                "net": 0.0,
            }
        nets[person_id]["net"] = round(
            nets[person_id]["net"] - float(split.get("amount_owed") or 0),
            2,
        )
    return list(nets.values())
