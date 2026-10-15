from agent.tools.debt_simplifier import simplify_debts
from db.crud import (
    compute_nets,
    init_db,
    insert_bill,
    insert_people,
    insert_settlement,
    insert_splits,
)
from db.models import People


def test_bill_nets_and_settlement_round_trip():
    session = init_db("sqlite:///:memory:")()
    raj = People(name="Raj", diet_pref="veg", drinks_alcohol=False)
    rahul = People(name="Rahul", diet_pref="non_veg", drinks_alcohol=True)
    assert insert_people(session, raj)
    assert insert_people(session, rahul)

    bill = insert_bill(
        session,
        image_url="bill.jpg",
        total=200.0,
        paid_by_id=raj.id,
        raw_json="{}",
    )
    insert_splits(
        session,
        bill.id,
        [
            {"id": raj.id, "amount_owed": 80.0},
            {"id": rahul.id, "amount_owed": 120.0},
        ],
    )

    nets = {row["name"]: row["net"] for row in compute_nets(session)}
    assert nets["Raj"] == 120.0
    assert nets["Rahul"] == -120.0
    payments = simplify_debts(compute_nets(session))
    assert payments[0]["from_name"] == "Rahul"
    assert payments[0]["to_name"] == "Raj"
    assert payments[0]["amount"] == 120.0

    insert_settlement(session, rahul.id, raj.id, 120.0)
    remaining = simplify_debts(compute_nets(session))
    assert remaining == []
    session.close()
