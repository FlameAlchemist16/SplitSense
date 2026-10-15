def simplify_debts(nets: list[dict], round_to: int = 2) -> list[dict]:
    """
    Collapse per-person nets into a small set of payments.

    Each net item: {"id": int, "name": str, "net": float}
    Positive net = others owe this person.
    Returns payments: from debtor -> creditor.
    """
    epsilon = 0.5 * (10 ** -round_to)

    debtors = []
    creditors = []
    for row in nets:
        net = round(float(row.get("net") or 0), round_to)
        item = {
            "id": row["id"],
            "name": row.get("name"),
            "remaining": abs(net),
        }
        if net < -epsilon:
            debtors.append(item)
        elif net > epsilon:
            creditors.append(item)

    debtors.sort(key=lambda item: item["remaining"], reverse=True)
    creditors.sort(key=lambda item: item["remaining"], reverse=True)

    payments = []
    i = 0
    j = 0
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        amount = round(min(debtor["remaining"], creditor["remaining"]), round_to)
        if amount > epsilon:
            payments.append(
                {
                    "from_id": debtor["id"],
                    "from_name": debtor["name"],
                    "to_id": creditor["id"],
                    "to_name": creditor["name"],
                    "amount": amount,
                }
            )
            debtor["remaining"] = round(debtor["remaining"] - amount, round_to)
            creditor["remaining"] = round(creditor["remaining"] - amount, round_to)
        if debtor["remaining"] <= epsilon:
            i += 1
        if creditor["remaining"] <= epsilon:
            j += 1

    return payments
