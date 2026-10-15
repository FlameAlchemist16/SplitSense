import json


def format_money(amount: float, currency: str = "INR") -> str:
    return f"{currency} {amount:.2f}"


def print_parsed_bill(bill_data: dict, currency: str = "INR") -> None:
    print("\n--- Parsed bill ---")
    items = bill_data.get("item_details") or []
    print(f"{'Item':<28} {'Qty':>4} {'Price':>10} {'Category':<10} {'Conf':>5}")
    for item in items:
        qty = item.get("quantity")
        qty_str = "" if qty is None else str(qty)
        print(
            f"{(item.get('item') or ''):<28} {qty_str:>4} "
            f"{(item.get('price') or 0):>10.2f} "
            f"{(item.get('category') or ''):<10} "
            f"{(item.get('confidence') or 0):>5.2f}"
        )
    validation = bill_data.get("total_validation") or {}
    if validation:
        print(
            f"\nOCR total: {validation.get('ocr_total')}  "
            f"Calculated: {validation.get('calculated_total')}  "
            f"Mismatch: {validation.get('mismatch')}"
        )


def print_splits(result: dict, currency: str, paid_by: str) -> None:
    print(f"\n--- Split (paid by {paid_by}) ---")
    print(
        f"{'Name':<16} {'Veg':>8} {'Non-veg':>9} {'Alcohol':>9} "
        f"{'Shared':>8} {'Tax':>8} {'Owes':>10}"
    )
    for split in result.get("splits") or []:
        print(
            f"{(split.get('name') or ''):<16} "
            f"{split.get('veg_amount', 0):>8.2f} "
            f"{split.get('non_veg_amount', 0):>9.2f} "
            f"{split.get('alcohol_amount', 0):>9.2f} "
            f"{split.get('shared_amount', 0):>8.2f} "
            f"{split.get('tax_amount', 0):>8.2f} "
            f"{format_money(split.get('amount_owed') or 0, currency):>10}"
        )
    warnings = result.get("warnings") or []
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")


def print_nets(nets: list[dict], title: str = "Net balances") -> None:
    print(f"\n--- {title} ---")
    print(f"{'Name':<16} {'Net':>10}")
    for row in nets:
        net = row.get("net", 0)
        label = "owed" if net > 0.004 else "owes" if net < -0.004 else "settled"
        print(f"{row.get('name', ''):<16} {net:>10.2f}  {label}")


def print_payments(payments: list[dict], currency: str, title: str) -> None:
    print(f"\n--- {title} ---")
    if not payments:
        print("All settled.")
        return
    for payment in payments:
        print(
            f"- {payment['from_name']} pays {payment['to_name']} "
            f"{format_money(payment['amount'], currency)}"
        )


def print_bill_json(bill_data: dict) -> None:
    print(json.dumps(bill_data, indent=2))
