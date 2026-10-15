import json
import sys

from sqlalchemy.orm import Session

from agent.agent_tools import AgentToolRunner
from agent.cli_display import (
    format_money,
    print_bill_json,
    print_nets,
    print_parsed_bill,
    print_payments,
    print_splits,
)
from agent.prompts import (
    ORCHESTRATOR_DEBT_REVISE_PROMPT,
    ORCHESTRATOR_INTAKE_PROMPT,
    ORCHESTRATOR_PARSE_REVISE_PROMPT,
    ORCHESTRATOR_SPLIT_REVISE_PROMPT,
)
from agent.react_loop import run_react_turn
from agent.tools.debt_simplifier import simplify_debts
from agent.workflow_state import Stage, WorkflowState
from db.crud import (
    compute_nets,
    compute_nets_with_pending_bill,
    fetch_people_metadata,
    get_or_create_group,
    init_db,
    insert_bill,
    insert_splits,
    list_people,
)


def bill_total(bill_data: dict, splits: list[dict]) -> float:
    validation = bill_data.get("total_validation") or {}
    total = validation.get("calculated_total")
    if total is None:
        total = sum(item.get("price") or 0 for item in bill_data.get("item_details") or [])
    if total is None:
        total = sum(split.get("amount_owed") or 0 for split in splits)
    return round(float(total), 2)


def _prompt_line(message: str) -> str:
    print(message)
    try:
        return input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(130)


def _approval_gate(stage_label: str) -> str:
    """Returns approve | revise | quit"""
    while True:
        choice = _prompt_line(
            f"\n[{stage_label}] Approve? [a]pprove  [r]evise (agent)  [j]son  [q]uit: "
        ).lower()
        if choice in ("a", "approve", ""):
            return "approve"
        if choice in ("r", "revise"):
            return "revise"
        if choice in ("j", "json"):
            return "json"
        if choice in ("q", "quit"):
            return "quit"
        print("Choose a, r, j, or q.")


def _run_intake(db: Session, state: WorkflowState, runner: AgentToolRunner) -> bool:
    print("\n=== SplitSense agent ===")
    print("Describe the bill and who is splitting. Type 'proceed' when ready to parse.")
    print("Type 'quit' to exit.\n")

    messages: list[dict] = []
    while True:
        user = _prompt_line("You:")
        if user.lower() in ("quit", "q", "exit"):
            return False
        if user.lower() in ("proceed", "continue", "go"):
            missing = state.intake_missing()
            if missing:
                print("Still missing: " + ", ".join(missing))
                continue
            state.stage = Stage.PARSE
            return True

        messages, reply = run_react_turn(
            system=ORCHESTRATOR_INTAKE_PROMPT,
            messages=messages,
            tool_runner=runner,
            user_input=user,
        )
        if reply:
            print(f"\nAgent: {reply}\n")


def _run_revision_chat(
    db: Session,
    state: WorkflowState,
    runner: AgentToolRunner,
    system: str,
    stage_label: str,
) -> bool:
    """ReAct chat until user types 'done'. Returns False if user quits."""
    messages: list[dict] = []
    print(f"\nRevision mode ({stage_label}). Describe changes, or type 'done' when finished.")
    while True:
        user = _prompt_line("You:")
        if user.lower() in ("quit", "q"):
            return False
        if user.lower() in ("done", "back"):
            return True
        messages, reply = run_react_turn(
            system=system,
            messages=messages,
            tool_runner=runner,
            user_input=user,
        )
        if reply:
            print(f"\nAgent: {reply}\n")


def _stage_parse(db: Session, state: WorkflowState, runner: AgentToolRunner) -> bool:
    from agent.tools.bill_parser import parse_bill

    print("\n=== Stage 1: Parse bill (OCR + LLM) ===")
    print("Running OCR and structuring…")
    state.parsed_bill = parse_bill(state.image_path)

    while True:
        print_parsed_bill(state.parsed_bill, state.currency)
        action = _approval_gate("Parsed bill")
        if action == "quit":
            return False
        if action == "json":
            print_bill_json(state.parsed_bill)
            continue
        if action == "approve":
            state.stage = Stage.SPLIT
            return True
        if not _run_revision_chat(db, state, runner, ORCHESTRATOR_PARSE_REVISE_PROMPT, "parse"):
            return False
        if state.parsed_bill:
            print_parsed_bill(state.parsed_bill, state.currency)


def _stage_split(db: Session, state: WorkflowState, runner: AgentToolRunner) -> bool:
    from agent.tools.split_engine import calculate_split

    print("\n=== Stage 2: Split bill ===")
    people = fetch_people_metadata(state.member_ids, db)
    paid_name = runner.name_by_id.get(state.paid_by_id, "?")

    if not state.split_result:
        state.split_result = calculate_split(
            state.parsed_bill,
            people,
            user_prompt=state.notes or "",
        )

    while True:
        print_splits(state.split_result, state.currency, paid_name)
        action = _approval_gate("Split")
        if action == "quit":
            return False
        if action == "json":
            print(json.dumps(state.split_result, indent=2))
            continue
        if action == "approve":
            state.stage = Stage.DEBT
            return True
        if not _run_revision_chat(db, state, runner, ORCHESTRATOR_SPLIT_REVISE_PROMPT, "split"):
            return False
        runner.dispatch("rerun_split", {})
        paid_name = runner.name_by_id.get(state.paid_by_id, "?")


def _stage_debt(db: Session, state: WorkflowState, runner: AgentToolRunner) -> bool:
    print("\n=== Stage 3: Debts (preview if this bill is saved) ===")
    splits = state.split_result.get("splits") or []
    total = bill_total(state.parsed_bill, splits)
    state.nets_preview = compute_nets_with_pending_bill(
        db,
        paid_by_id=state.paid_by_id,
        total=total,
        splits=splits,
    )
    state.debt_preview = simplify_debts(state.nets_preview)

    while True:
        print_nets(state.nets_preview, "Net balances (including this bill)")
        print_payments(state.debt_preview, state.currency, "Simplified payments")
        action = _approval_gate("Debts")
        if action == "quit":
            return False
        if action == "json":
            print(json.dumps({"nets": state.nets_preview, "payments": state.debt_preview}, indent=2))
            continue
        if action == "approve":
            state.stage = Stage.COMMIT
            return True
        if not _run_revision_chat(db, state, runner, ORCHESTRATOR_DEBT_REVISE_PROMPT, "debts"):
            return False
        state.nets_preview = compute_nets_with_pending_bill(
            db,
            paid_by_id=state.paid_by_id,
            total=total,
            splits=state.split_result.get("splits") or [],
        )
        state.debt_preview = simplify_debts(state.nets_preview)


def _stage_commit(db: Session, state: WorkflowState) -> bool:
    print("\n=== Stage 4: Save to database ===")
    splits = state.split_result.get("splits") or []
    total = bill_total(state.parsed_bill, splits)
    group_id = None
    if state.group_name:
        group = get_or_create_group(db, state.group_name, state.member_ids)
        group_id = group.id

    bill = insert_bill(
        db,
        image_url=state.image_path,
        total=total,
        paid_by_id=state.paid_by_id,
        raw_json=json.dumps(state.parsed_bill),
        currency=state.currency,
        group_id=group_id,
        notes=state.notes or None,
    )
    insert_splits(db, bill.id, splits)
    state.committed_bill_id = bill.id
    state.stage = Stage.DONE

    print(f"\nSaved bill #{bill.id}  total {format_money(total, state.currency)}")
    print_payments(
        simplify_debts(compute_nets(db)),
        state.currency,
        "Simplified debts (database)",
    )
    return True


def run_interactive_agent() -> int:
    SessionFactory = init_db()
    db = SessionFactory()
    state = WorkflowState()
    name_by_id = {p.id: p.name for p in list_people(db)}
    runner = AgentToolRunner(db, state, name_by_id)

    try:
        if not _run_intake(db, state, runner):
            return 0
        if not _stage_parse(db, state, runner):
            return 0
        if not _stage_split(db, state, runner):
            return 0
        if not _stage_debt(db, state, runner):
            return 0
        if not _stage_commit(db, state):
            return 0
        print("\nDone. Balances are updated in SQLite.")
        return 0
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()
