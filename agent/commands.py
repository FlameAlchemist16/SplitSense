import argparse
import json
import sys
from typing import Sequence

from agent.cli_display import format_money, print_payments, print_splits
from agent.tools.debt_simplifier import simplify_debts
from db.crud import (
    compute_nets,
    get_or_create_group,
    get_people_by_names,
    init_db,
    insert_bill,
    insert_people,
    insert_settlement,
    insert_splits,
    list_bills,
    list_people,
    people_to_split_dicts,
)
from db.models import People


def parse_name_list(raw: str) -> list[str]:
    names = [name.strip() for name in raw.split(",") if name.strip()]
    if not names:
        raise ValueError("Provide at least one person name")
    return names


def bill_total(bill_data: dict, splits: list[dict]) -> float:
    validation = bill_data.get("total_validation") or {}
    total = validation.get("calculated_total")
    if total is None:
        total = sum(item.get("price") or 0 for item in bill_data.get("item_details") or [])
    if total is None:
        total = sum(split.get("amount_owed") or 0 for split in splits)
    return round(float(total), 2)


def add_split_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bill", required=True, help="Path to bill image (.jpg/.jpeg/.png)")
    parser.add_argument("--people", required=True, help='Comma-separated names, e.g. "Raj, Rahul, James"')
    parser.add_argument("--notes", default="", help="Natural-language split overrides")
    parser.add_argument("--paid-by", dest="paid_by", default=None, help="Who paid. Defaults to the first person")
    parser.add_argument("--group", default=None, help="Optional group name to attach this bill to")
    parser.add_argument("--currency", default="INR")


def cmd_people_add(args: argparse.Namespace) -> int:
    session = init_db()()
    person = People(
        name=args.name.strip(),
        diet_pref=args.diet,
        drinks_alcohol=bool(args.drinks),
        phone=args.phone,
        email=args.email,
    )
    if not insert_people(session, person):
        return 1
    session.close()
    return 0


def cmd_people_list(_args: argparse.Namespace) -> int:
    session = init_db()()
    people = list_people(session)
    if not people:
        print("No people yet. Add one with: python -m agent.core people add --name Raj --diet veg")
        session.close()
        return 0
    print(f"{'ID':<4} {'Name':<16} {'Diet':<8} {'Drinks':<7}")
    for person in people:
        print(
            f"{person.id:<4} {person.name:<16} {person.diet_pref:<8} "
            f"{'yes' if person.drinks_alcohol else 'no':<7}"
        )
    session.close()
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    names = parse_name_list(args.people)
    paid_by_name = (args.paid_by or names[0]).strip()
    session = init_db()()
    people_rows = get_people_by_names(session, names)
    paid_by_row = get_people_by_names(session, [paid_by_name])[0]
    people = people_to_split_dicts(people_rows)

    from agent.tools.bill_parser import parse_bill
    from agent.tools.split_engine import calculate_split

    print("Reading bill...")
    bill_data = parse_bill(args.bill)
    result = calculate_split(bill_data, people, user_prompt=args.notes or "")
    total = bill_total(bill_data, result.get("splits") or [])
    currency = args.currency

    group_id = None
    if args.group:
        group = get_or_create_group(session, args.group, [row.id for row in people_rows])
        group_id = group.id

    bill = insert_bill(
        session,
        image_url=args.bill,
        total=total,
        paid_by_id=paid_by_row.id,
        raw_json=json.dumps(bill_data),
        currency=currency,
        group_id=group_id,
        notes=args.notes or None,
    )
    insert_splits(session, bill.id, result.get("splits") or [])

    validation = bill_data.get("total_validation") or {}
    print(f"\nBill #{bill.id}  total {format_money(total, currency)}")
    if validation.get("ocr_total") is not None:
        print(f"OCR total: {validation.get('ocr_total')}  mismatch: {validation.get('mismatch')}")
    print_splits(result, currency, paid_by_row.name)
    print_payments(simplify_debts(compute_nets(session)), currency, "Simplified debts")
    session.close()
    return 0


def cmd_balances(_args: argparse.Namespace) -> int:
    session = init_db()()
    nets = compute_nets(session)
    print(f"{'Name':<16} {'Net':>10}")
    for row in nets:
        net = row["net"]
        label = "owed" if net > 0.004 else "owes" if net < -0.004 else "settled"
        print(f"{row['name']:<16} {net:>10.2f}  {label}")
    session.close()
    return 0


def cmd_debts(_args: argparse.Namespace) -> int:
    session = init_db()()
    print_payments(simplify_debts(compute_nets(session)), "INR", "Simplified debts")
    session.close()
    return 0


def cmd_settle(args: argparse.Namespace) -> int:
    session = init_db()()
    payer = get_people_by_names(session, [args.payer])[0]
    payee = get_people_by_names(session, [args.payee])[0]
    row = insert_settlement(session, payer.id, payee.id, args.amount, note=args.note)
    print(f"Recorded settlement #{row.id}: {payer.name} paid {payee.name} {args.amount:.2f}")
    print_payments(simplify_debts(compute_nets(session)), "INR", "Remaining debts")
    session.close()
    return 0


def cmd_bills(_args: argparse.Namespace) -> int:
    session = init_db()()
    bills = list_bills(session)
    if not bills:
        print("No bills stored yet.")
        session.close()
        return 0
    print(f"{'ID':<4} {'Date':<20} {'Total':>10} {'Paid by':<16} {'Image'}")
    for bill in bills:
        paid_by = bill.paid_by.name if bill.paid_by else str(bill.paid_by_id)
        date = bill.date.isoformat(sep=" ", timespec="minutes") if bill.date else ""
        print(f"{bill.id:<4} {date:<20} {bill.total:>10.2f} {paid_by:<16} {bill.image_url}")
    session.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.core",
        description="SplitSense: interactive agent (default) or direct admin commands.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("chat", help="Interactive ReAct agent with staged approvals (default)")

    split_parser = sub.add_parser("split", help="One-shot parse + split + save (no approvals)")
    add_split_args(split_parser)

    people_parser = sub.add_parser("people", help="Manage people profiles")
    people_sub = people_parser.add_subparsers(dest="people_cmd")
    add_parser = people_sub.add_parser("add", help="Add a person")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--diet", required=True, choices=["veg", "non_veg"])
    add_parser.add_argument("--drinks", action="store_true", help="This person drinks alcohol")
    add_parser.add_argument("--phone", default=None)
    add_parser.add_argument("--email", default=None)
    people_sub.add_parser("list", help="List people")

    sub.add_parser("balances", help="Show net balance per person")
    sub.add_parser("debts", help="Show simplified settlement payments")
    sub.add_parser("bills", help="List stored bills")

    settle_parser = sub.add_parser("settle", help="Record a payment")
    settle_parser.add_argument("--from", dest="payer", required=True, help="Who paid")
    settle_parser.add_argument("--to", dest="payee", required=True, help="Who received")
    settle_parser.add_argument("--amount", required=True, type=float)
    settle_parser.add_argument("--note", default=None)
    return parser


def normalize_argv(argv: Sequence[str]) -> list[str]:
    args = list(argv)
    commands = {"chat", "split", "people", "balances", "debts", "settle", "bills"}
    if args and args[0] not in commands:
        args = ["split", *args]
    return args


def dispatch(args: argparse.Namespace) -> int:
    if args.command in (None, "chat"):
        from agent.orchestrator import run_interactive_agent

        return run_interactive_agent()
    if args.command == "split":
        return cmd_split(args)
    if args.command == "people":
        if args.people_cmd == "add":
            return cmd_people_add(args)
        if args.people_cmd == "list":
            return cmd_people_list(args)
        print("Use: python -m agent.core people add|list")
        return 2
    if args.command == "balances":
        return cmd_balances(args)
    if args.command == "debts":
        return cmd_debts(args)
    if args.command == "settle":
        return cmd_settle(args)
    if args.command == "bills":
        return cmd_bills(args)
    return 2


def run_cli(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not argv:
        return dispatch(argparse.Namespace(command=None))
    args = parser.parse_args(normalize_argv(argv))
    try:
        return dispatch(args)
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
