def split_amount(items, person_id, person_list):
    """
    Split total amount of given items equally among people.
    """

    if (person_id not in person_list) or len(person_list) == 0:
        return 0

    total_amount = sum(item.get("price") or 0 for item in items)

    return total_amount / len(person_list)


def calculate_proportional_tax(tax_items, pretax_amount, total_pretax):
    """
    Calculate proportional tax share based on pretax contribution.
    """

    total_tax = sum(item.get("price") or 0 for item in tax_items)

    if total_pretax == 0:
        return 0

    return (pretax_amount / total_pretax) * total_tax


def calculate_person_splits(categorized_items: dict, people: list[dict]):

    results = {
        "splits": [],
        "warnings": []
    }

    # Calculate total pretax bill amount
    total_pretax = 0

    for category in categorized_items:

        if category not in ("tax_items", "unknown_items"):

            total_pretax += sum(
                item.get("price") or 0
                for item in categorized_items[category]["item_list"]
            )

    for person in people:

        person_id = person.get("id")

        breakdown = {
            "id": person_id,
            "name": person.get("name"),
            "veg_amount": 0,
            "non_veg_amount": 0,
            "alcohol_amount": 0,
            "shared_amount": 0,
            "tax_amount": 0,
            "amount_owed": 0
        }

        # Veg split
        breakdown["veg_amount"] = split_amount(
            categorized_items["veg_items"]["item_list"],
            person_id,
            categorized_items["veg_items"]["person_list"]
        )

        # Non Veg split
        breakdown["non_veg_amount"] = split_amount(
            categorized_items["non_veg_items"]["item_list"],
            person_id,
            categorized_items["non_veg_items"]["person_list"]
        )

        # Alcohol split
        breakdown["alcohol_amount"] = split_amount(
            categorized_items["alcohol_items"]["item_list"],
            person_id,
            categorized_items["alcohol_items"]["person_list"]
        )

        # Shared split
        breakdown["shared_amount"] = split_amount(
            categorized_items["shared_items"]["item_list"],
            person_id,
            categorized_items["shared_items"]["person_list"]
        )

        # Person pretax subtotal
        pretax_amount = (
            breakdown["veg_amount"]
            + breakdown["non_veg_amount"]
            + breakdown["alcohol_amount"]
            + breakdown["shared_amount"]
        )

        # Tax split proportionally
        breakdown["tax_amount"] = calculate_proportional_tax(
            categorized_items["tax_items"]["item_list"],
            pretax_amount,
            total_pretax
        )

        # Final total
        breakdown["amount_owed"] = (
            pretax_amount + breakdown["tax_amount"]
        )

        # Round values safely
        for key, value in breakdown.items():

            if isinstance(value, (int, float)):
                breakdown[key] = round(value, 2)

        results["splits"].append(breakdown)

    return results


def filter_people(people: list[dict], categorized_items: dict):

    for info in people:

        person_id = info.get('id')

        if not person_id:
            continue

        if info.get('diet_pref') == "veg":

            if person_id not in categorized_items['veg_items']['person_list']:
                categorized_items['veg_items']['person_list'].append(person_id)

        elif info.get('diet_pref') == "non_veg":

            if person_id not in categorized_items['non_veg_items']['person_list']:
                categorized_items['non_veg_items']['person_list'].append(person_id)

        if info.get('drinks_alcohol') is True:

            if person_id not in categorized_items['alcohol_items']['person_list']:
                categorized_items['alcohol_items']['person_list'].append(person_id)

        # Shared among everyone
        if person_id not in categorized_items['shared_items']['person_list']:
            categorized_items['shared_items']['person_list'].append(person_id)

        # Tax shared among everyone
        if person_id not in categorized_items['tax_items']['person_list']:
            categorized_items['tax_items']['person_list'].append(person_id)

    return categorized_items


def filter_items(bill_data: dict, categorized_items: dict):

    for item in bill_data.get('item_details', []):

        category = item.get("category")

        if category not in ["veg", "non_veg", "alcohol", "shared", "tax"]:
            category = "unknown"

        categorized_items[f"{category}_items"]["item_list"].append(item)

    return categorized_items


def calculate_split(bill_data: dict, people: list[dict]) -> dict:
    """
    Takes structured bill data from bill parser.
    Takes list of people with their preferences.

    Returns:
    {
        "splits": [...],
        "warnings": [...]
    }
    """

    categorized_items = {
        'veg_items': {
            'item_list': [],
            'person_list': []
        },

        'non_veg_items': {
            'item_list': [],
            'person_list': []
        },

        'alcohol_items': {
            'item_list': [],
            'person_list': []
        },

        'shared_items': {
            'item_list': [],
            'person_list': []
        },

        'tax_items': {
            'item_list': [],
            'person_list': []
        },

        'unknown_items': {
            'item_list': [],
            'person_list': []
        }
    }

    categorized_items = filter_items(
        bill_data=bill_data,
        categorized_items=categorized_items
    )

    categorized_items = filter_people(
        people=people,
        categorized_items=categorized_items
    )

    warnings = []

    # Check categories with items but no eligible people
    for category in ["veg", "non_veg", "alcohol"]:

        category_data = categorized_items[f"{category}_items"]

        if (
            len(category_data["item_list"]) > 0 and
            len(category_data["person_list"]) == 0
        ):

            warnings.append(
                f"{category} items exist but no eligible people found."
            )

    # Check for unknown items
    unknown_items = categorized_items["unknown_items"]["item_list"]

    if len(unknown_items) > 0:

        unknown_item_names = sorted(set(
            item.get("item", "Unknown Item")
            for item in unknown_items
        ))

        warnings.append(
            "Unknown category items found -> "
            + ", ".join(unknown_item_names)
        )

    results = calculate_person_splits(
        categorized_items=categorized_items,
        people=people
    )

    results["warnings"] = warnings

    return results