from agent.tools.debt_simplifier import simplify_debts


def test_cycle_collapses_to_one_payment():
    payments = simplify_debts(
        [
            {"id": 1, "name": "A", "net": -100},
            {"id": 2, "name": "B", "net": 0},
            {"id": 3, "name": "C", "net": 100},
        ]
    )
    assert payments == [
        {
            "from_id": 1,
            "from_name": "A",
            "to_id": 3,
            "to_name": "C",
            "amount": 100.0,
        }
    ]


def test_one_debtor_two_creditors():
    payments = simplify_debts(
        [
            {"id": 1, "name": "A", "net": -200},
            {"id": 2, "name": "B", "net": 50},
            {"id": 3, "name": "C", "net": 150},
        ]
    )
    assert payments == [
        {
            "from_id": 1,
            "from_name": "A",
            "to_id": 3,
            "to_name": "C",
            "amount": 150.0,
        },
        {
            "from_id": 1,
            "from_name": "A",
            "to_id": 2,
            "to_name": "B",
            "amount": 50.0,
        },
    ]


def test_settled_nets_need_no_payments():
    assert simplify_debts(
        [
            {"id": 1, "name": "A", "net": 0},
            {"id": 2, "name": "B", "net": 0.001},
        ]
    ) == []
