from agent.tools.split_engine import apply_overrides, calculate_split

BILL = {
    "item_details": [
        {"item": "Paneer Tikka", "price": 300.0, "category": "veg"},
        {"item": "Chicken", "price": 300.0, "category": "non_veg"},
        {"item": "Beer", "price": 200.0, "category": "alcohol"},
        {"item": "Bread", "price": 90.0, "category": "shared"},
        {"item": "Tax", "price": 89.0, "category": "tax"},
    ]
}

PEOPLE = [
    {"id": 1, "name": "Raj", "diet_pref": "veg", "drinks_alcohol": False},
    {"id": 2, "name": "Rahul", "diet_pref": "non_veg", "drinks_alcohol": True},
    {"id": 3, "name": "James", "diet_pref": "veg", "drinks_alcohol": True},
]


def _by_name(result):
    return {row["name"]: row for row in result["splits"]}


def test_category_rules_and_proportional_tax():
    result = calculate_split(BILL, PEOPLE)
    splits = _by_name(result)
    assert splits["Raj"]["veg_amount"] == 150.0
    assert splits["Raj"]["non_veg_amount"] == 0.0
    assert splits["Raj"]["alcohol_amount"] == 0.0
    assert splits["Raj"]["shared_amount"] == 30.0
    assert splits["Rahul"]["non_veg_amount"] == 300.0
    assert splits["Rahul"]["alcohol_amount"] == 100.0
    assert splits["James"]["alcohol_amount"] == 100.0
    assert round(sum(row["amount_owed"] for row in result["splits"]), 2) == 979.0


def test_exclude_alcohol_override():
    categorized = {
        "veg_items": [],
        "non_veg_items": [],
        "alcohol_items": [{"item": "Beer", "price": 200.0, "person_list": [2, 3]}],
        "shared_items": [],
        "tax_items": [],
        "unknown_items": [],
    }
    updated, errors = apply_overrides(
        categorized,
        {
            "include": [],
            "exclude": [{"person_list": [3], "category": "alcohol", "item_name": None}],
            "replace": [],
        },
    )
    assert errors == []
    assert updated["alcohol_items"][0]["person_list"] == [2]


def test_unknown_category_warns():
    result = calculate_split(
        {"item_details": [{"item": "Mystery", "price": 10.0, "category": "dessert"}]},
        PEOPLE,
    )
    assert any("Mystery" in warning for warning in result["warnings"])
