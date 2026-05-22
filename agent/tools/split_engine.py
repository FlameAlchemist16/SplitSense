def split_amount(items, person_id, person_list):
    pass

def calculate_proportional_tax(tax_items, pretax_amount, total_pretax):
    pass

def calculate_person_splits(categorized_items: dict, people: list[dict]):
    
    pass

def filter_people(people: list[dict], item_category: dict):

    for info in people:

        person_id = info.get('id')

        if info.get('diet_pref') == "veg":
            item_category['veg_items']['person_list'].append(person_id)

        elif info.get('diet_pref') == "non_veg":
            item_category['non_veg_items']['person_list'].append(person_id)

        if info.get('drinks_alcohol') is True:
            item_category['alcohol_items']['person_list'].append(person_id)

        # Shared among everyone
        item_category['shared_items']['person_list'].append(person_id)

        # tax shared among everyone
        item_category['tax_items']['person_list'].append(person_id)

    return item_category

def calculate_split(bill_data: dict, people: list[dict]) -> list[dict]:
    """
    Takes structured bill data from bill parser.
    Takes list of people with their preferences.
    Returns per-person amount breakdown.
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

    for item in bill_data.get('item_details', []):

        category = item.get("category")

        if category not in ["veg", "non_veg", "alcohol", "shared", "tax"]:
            category = "unknown"

        categorized_items[f"{category}_items"]["item_list"].append(item)

    categorized_items = filter_people(
        people=people,
        item_category=categorized_items
    )

    return categorized_items