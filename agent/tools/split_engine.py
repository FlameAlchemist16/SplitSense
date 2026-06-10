from agent.llm_client import LLM_MODEL, haiku_client
from agent.prompts import OVERRIDE_PARSER_SYSTEM_PROMPT
import json

def split_amount(
        items,
        person_id
):
    """
    Split total amount of given items among eligible people.
    Item-level person assignment.
    """

    total_amount = 0

    for item in items:

        person_list = item.get("person_list", [])

        if (
            person_id in person_list
            and len(person_list) > 0
        ):
            total_amount += (
                (item.get("price") or 0)
                / len(person_list)
            )

    return total_amount


def calculate_proportional_tax(
    tax_items,
    pretax_amount,
    total_pretax
):
    """
    Calculate proportional tax share based on pretax contribution.
    """

    total_tax = sum(
        item.get("price") or 0
        for item in tax_items
    )

    if total_pretax == 0:
        return 0

    return (
        (pretax_amount / total_pretax)
        * total_tax
    )


def assign_people_to_items(
    categorized_items: dict,
    people: list[dict]
):
    """
    Assign eligible people to each item.
    """

    veg_people = []
    non_veg_people = []
    alcohol_people = []
    all_people = []

    for person in people:

        person_id = person.get("id")

        if not person_id:
            continue

        all_people.append(person_id)

        if person.get("diet_pref") == "veg":
            veg_people.append(person_id)

        elif person.get("diet_pref") == "non_veg":
            non_veg_people.append(person_id)

        if person.get("drinks_alcohol") is True:
            alcohol_people.append(person_id)

    for item in categorized_items["veg_items"]:
        item["person_list"] = veg_people.copy()

    for item in categorized_items["non_veg_items"]:
        item["person_list"] = non_veg_people.copy()

    for item in categorized_items["alcohol_items"]:
        item["person_list"] = alcohol_people.copy()

    for item in categorized_items["shared_items"]:
        item["person_list"] = all_people.copy()

    for item in categorized_items["tax_items"]:
        item["person_list"] = all_people.copy()

    return categorized_items


def filter_items(
    bill_data: dict,
    categorized_items: dict
):

    for item in bill_data.get("item_details", []):

        category = item.get("category")

        if category not in [
            "veg",
            "non_veg",
            "alcohol",
            "shared",
            "tax"
        ]:
            category = "unknown"

        item_copy = item.copy()
        item_copy["person_list"] = []

        categorized_items[
            f"{category}_items"
        ].append(item_copy)

    return categorized_items


def calculate_person_splits(
    categorized_items: dict,
    people: list[dict]
):

    results = {
        "splits": [],
        "warnings": []
    }

    # Calculate total pretax bill amount
    total_pretax = 0

    for category in categorized_items:

        if category not in (
            "tax_items",
            "unknown_items"
        ):

            total_pretax += sum(
                item.get("price") or 0
                for item in categorized_items[category]
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

        breakdown["veg_amount"] = split_amount(
            categorized_items["veg_items"],
            person_id
        )

        breakdown["non_veg_amount"] = split_amount(
            categorized_items["non_veg_items"],
            person_id
        )

        breakdown["alcohol_amount"] = split_amount(
            categorized_items["alcohol_items"],
            person_id
        )

        breakdown["shared_amount"] = split_amount(
            categorized_items["shared_items"],
            person_id
        )

        pretax_amount = (
            breakdown["veg_amount"]
            + breakdown["non_veg_amount"]
            + breakdown["alcohol_amount"]
            + breakdown["shared_amount"]
        )

        breakdown["tax_amount"] = (
            calculate_proportional_tax(
                categorized_items["tax_items"],
                pretax_amount,
                total_pretax
            )
        )

        breakdown["amount_owed"] = (
            pretax_amount
            + breakdown["tax_amount"]
        )

        for key, value in breakdown.items():

            if isinstance(value, (int, float)):
                breakdown[key] = round(value, 2)

        results["splits"].append(
            breakdown
        )

    return results


def calculate_split(
    bill_data: dict,
    people: list[dict],
    user_prompt: str = ""
) -> dict:
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
        "veg_items": [],
        "non_veg_items": [],
        "alcohol_items": [],
        "shared_items": [],
        "tax_items": [],
        "unknown_items": []
    }

    categorized_items = filter_items(
        bill_data=bill_data,
        categorized_items=categorized_items
    )

    categorized_items = assign_people_to_items(
        categorized_items=categorized_items,
        people=people
    )
    
    warnings = []

    if user_prompt:
        overrides = parse_overrides_with_llm(prompt=user_prompt,people=people,categorized_items=categorized_items)

        categorized_items, override_errors = apply_overrides(categorized_items, overrides)
        warnings.extend(override_errors)

    # Validate eligible people assignment
    for category in [
        "veg_items",
        "non_veg_items",
        "alcohol_items"
    ]:

        for item in categorized_items[category]:

            if len(item.get("person_list", [])) == 0:

                warnings.append(
                    f"{item.get('item', 'Unknown Item')} "
                    f"has no eligible people."
                )

    # Unknown item validation
    unknown_items = categorized_items[
        "unknown_items"
    ]

    if len(unknown_items) > 0:

        unknown_item_names = sorted(
            set(
                item.get(
                    "item",
                    "Unknown Item"
                )
                for item in unknown_items
            )
        )

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

def parse_overrides_with_llm(
    prompt: str,
    people: list[dict],
    categorized_items: dict
) -> dict:

    item_list = [
    {"item": item.get("item"), "category": category.replace("_items", "")}
    for category, items in categorized_items.items()
        for item in items
            if category != "unknown_items"
    ]

    people_modified = [{"id": p.get("id"), "name": p.get("name")} for p in people]

    user_prompt = f"""
    Use these for your task - 

    1. The user prompt given in the input: {prompt}
    2. The people list[dict]: {people_modified}
    3. The categorized_items dict: {item_list}
    """
    haiku_response = haiku_client.messages.create(
        model=LLM_MODEL,
        system=OVERRIDE_PARSER_SYSTEM_PROMPT,
        max_tokens=5000,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    haiku_string = haiku_response.content[0].text

    haiku_string = haiku_string.strip()

    if "```" in haiku_string:
        haiku_string = haiku_string.split("```")[1]

        if haiku_string.startswith("json"):
            haiku_string = haiku_string[4:]
        
        haiku_string = haiku_string.strip()

    try:
        haiku_dict = json.loads(haiku_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Haiku returned invalid JSON: {e}\nRaw response: {haiku_string}")

    return haiku_dict[0] if isinstance(haiku_dict, list) else haiku_dict

def apply_overrides(
    categorized_items: dict,
    overrides: dict
) -> tuple[dict, list[str]]:
    """
    Applies include, exclude and replace overrides.
    Returns:
        (
            updated_categorized_items,
            errors
        )
    """
    errors = []

    def get_matching_items(
        category: str,
        item_name: str | None
    ):
        category_key = f"{category}_items"

        if category_key not in categorized_items:
            errors.append(
                f"Category '{category}' does not exist."
            )
            return []

        items = categorized_items[category_key]

        # Category-level rule
        if item_name is None:
            return items

        matching_items = [
            item
            for item in items
            if item.get("item") == item_name
        ]

        if not matching_items:
            errors.append(
                f"Item '{item_name}' not found in category '{category}'."
            )
            return []
        return matching_items

    operations = {
        "exclude": lambda item, person_ids: [
            pid
            for pid in item["person_list"]
            if pid not in person_ids
        ],
        "include": lambda item, person_ids: (
            item["person_list"]
            + [
                pid
                for pid in person_ids
                if pid not in item["person_list"]
            ]
        ),
        "replace": lambda item, person_ids: (
            person_ids.copy()
        )
    }

    for operation, update_fn in operations.items():
        for rule in overrides.get(operation, []):
            matching_items = get_matching_items(
                category=rule.get("category"),
                item_name=rule.get("item_name")
            )

            if not matching_items:
                continue

            for item in matching_items:
                item["person_list"] = update_fn(
                    item,
                    rule.get("person_list", [])
                )
    return categorized_items, errors