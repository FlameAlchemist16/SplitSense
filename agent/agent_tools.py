import json
import os
from typing import Any, Callable

from sqlalchemy.orm import Session

from agent.workflow_state import WorkflowState
from db.crud import (
    fetch_people_metadata,
    get_group_member_ids,
    get_or_create_group,
    get_people_by_names,
    insert_people,
    list_groups,
    list_people,
)
from db.models import People


def _person_row(person: People) -> dict:
    return {
        "id": person.id,
        "name": person.name,
        "diet_pref": person.diet_pref,
        "drinks_alcohol": bool(person.drinks_alcohol),
    }


class AgentToolRunner:
    def __init__(self, db: Session, state: WorkflowState, name_by_id: dict[int, str]):
        self.db = db
        self.state = state
        self.name_by_id = name_by_id
        self._refresh_names()

    def _refresh_names(self) -> None:
        for person in list_people(self.db):
            self.name_by_id[person.id] = person.name

    def _resolve_person_id(self, name: str) -> int:
        return get_people_by_names(self.db, [name.strip()])[0].id

    def dispatch(self, name: str, arguments: dict) -> Any:
        handlers: dict[str, Callable[[dict], Any]] = {
            "get_workflow_status": self._get_workflow_status,
            "list_people": self._list_people,
            "list_groups": self._list_groups,
            "load_group_members": self._load_group_members,
            "register_person": self._register_person,
            "set_bill_image": self._set_bill_image,
            "set_member_names": self._set_member_names,
            "set_paid_by": self._set_paid_by,
            "set_split_notes": self._set_split_notes,
            "set_group_name": self._set_group_name,
            "update_parsed_bill": self._update_parsed_bill,
            "rerun_bill_parse": self._rerun_bill_parse,
            "rerun_split": self._rerun_split,
        }
        if name not in handlers:
            return {"error": f"Unknown tool: {name}"}
        return handlers[name](arguments or {})

    def _get_workflow_status(self, _args: dict) -> dict:
        return self.state.snapshot_for_agent(self.name_by_id)

    def _list_people(self, _args: dict) -> list[dict]:
        return [_person_row(p) for p in list_people(self.db)]

    def _list_groups(self, _args: dict) -> list[dict]:
        return list_groups(self.db)

    def _load_group_members(self, args: dict) -> dict:
        group_name = args.get("group_name", "").strip()
        if not group_name:
            return {"error": "group_name is required"}
        member_ids = get_group_member_ids(self.db, group_name)
        self.state.group_name = group_name
        self.state.member_ids = member_ids
        self._refresh_names()
        return {
            "group_name": group_name,
            "member_ids": member_ids,
            "member_names": [self.name_by_id[mid] for mid in member_ids],
        }

    def _register_person(self, args: dict) -> dict:
        name = (args.get("name") or "").strip()
        diet = args.get("diet_pref")
        if not name or diet not in ("veg", "non_veg"):
            return {"error": "name and diet_pref (veg|non_veg) are required"}
        person = People(
            name=name,
            diet_pref=diet,
            drinks_alcohol=bool(args.get("drinks_alcohol")),
        )
        if not insert_people(self.db, person, quiet=True):
            return {"error": "failed to insert person"}
        self._refresh_names()
        if args.get("add_to_members", True):
            if person.id not in self.state.member_ids:
                self.state.member_ids.append(person.id)
        return _person_row(person)

    def _set_bill_image(self, args: dict) -> dict:
        path = (args.get("path") or "").strip()
        if not path:
            return {"error": "path is required"}
        if not os.path.exists(path):
            return {"error": f"file not found: {path}"}
        if not path.lower().endswith((".png", ".jpeg", ".jpg")):
            return {"error": "use .png, .jpeg, or .jpg"}
        self.state.image_path = path
        return {"image_path": path}

    def _set_member_names(self, args: dict) -> dict:
        names = args.get("names") or []
        if not names:
            return {"error": "names list is required"}
        people = get_people_by_names(self.db, [str(n).strip() for n in names])
        self.state.member_ids = [p.id for p in people]
        return {
            "member_ids": self.state.member_ids,
            "member_names": [p.name for p in people],
        }

    def _set_paid_by(self, args: dict) -> dict:
        name = (args.get("name") or "").strip()
        if not name:
            return {"error": "name is required"}
        paid_id = self._resolve_person_id(name)
        self.state.paid_by_id = paid_id
        result = {"paid_by_id": paid_id, "paid_by": name}
        if self.state.member_ids and paid_id not in self.state.member_ids:
            result["warning"] = "payer is not in the current member list"
        return result

    def _set_split_notes(self, args: dict) -> dict:
        self.state.notes = (args.get("notes") or "").strip()
        return {"notes": self.state.notes}

    def _set_group_name(self, args: dict) -> dict:
        name = (args.get("name") or "").strip()
        if not name:
            return {"error": "name is required"}
        self.state.group_name = name
        if self.state.member_ids:
            get_or_create_group(self.db, name, self.state.member_ids)
        return {"group_name": name}

    def _update_parsed_bill(self, args: dict) -> dict:
        if self.state.parsed_bill is None:
            return {"error": "no parsed bill yet"}
        patch = args.get("bill_json")
        if isinstance(patch, str):
            try:
                patch = json.loads(patch)
            except json.JSONDecodeError as exc:
                return {"error": f"invalid JSON: {exc}"}
        if not isinstance(patch, dict):
            return {"error": "bill_json object is required"}
        self.state.parsed_bill = patch
        return {"ok": True, "item_count": len(patch.get("item_details") or [])}

    def _rerun_bill_parse(self, args: dict) -> dict:
        if not self.state.image_path:
            return {"error": "bill image not set"}
        from agent.tools.bill_parser import parse_bill

        hint = (args.get("hint") or "").strip()
        if hint:
            from agent.tools.bill_parser import extract_text_from_image, structure_bill_with_llm

            ocr = extract_text_from_image(self.state.image_path)
            ocr["text"] = f"{ocr.get('text', '')} USER_HINT: {hint}"
            self.state.parsed_bill = structure_bill_with_llm(ocr)
        else:
            self.state.parsed_bill = parse_bill(self.state.image_path)
        return {
            "ok": True,
            "item_count": len(self.state.parsed_bill.get("item_details") or []),
        }

    def _rerun_split(self, _args: dict) -> dict:
        if not self.state.parsed_bill:
            return {"error": "parsed bill missing"}
        if not self.state.member_ids:
            return {"error": "members missing"}
        from agent.tools.split_engine import calculate_split

        people = fetch_people_metadata(self.state.member_ids, self.db)
        self.state.split_result = calculate_split(
            self.state.parsed_bill,
            people,
            user_prompt=self.state.notes or "",
        )
        return {
            "ok": True,
            "split_count": len(self.state.split_result.get("splits") or []),
            "warnings": self.state.split_result.get("warnings") or [],
        }


TOOL_DEFINITIONS = [
    {
        "name": "get_workflow_status",
        "description": "Current workflow stage, intake fields, and what is still missing.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_people",
        "description": "List all people in the database with diet and alcohol preferences.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_groups",
        "description": "List saved groups and their member names.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "load_group_members",
        "description": "Load an existing group into the current bill session.",
        "input_schema": {
            "type": "object",
            "properties": {"group_name": {"type": "string"}},
            "required": ["group_name"],
        },
    },
    {
        "name": "register_person",
        "description": "Create a new person in the database (and add to bill members by default).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "diet_pref": {"type": "string", "enum": ["veg", "non_veg"]},
                "drinks_alcohol": {"type": "boolean"},
                "add_to_members": {"type": "boolean"},
            },
            "required": ["name", "diet_pref"],
        },
    },
    {
        "name": "set_bill_image",
        "description": "Set the local path to the bill photo for this session.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "set_member_names",
        "description": "Set bill participants by name (must already exist in DB).",
        "input_schema": {
            "type": "object",
            "properties": {
                "names": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["names"],
        },
    },
    {
        "name": "set_paid_by",
        "description": "Set who paid the bill (must be a participant).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "set_split_notes",
        "description": "Natural-language override rules for splitting (e.g. who skipped alcohol).",
        "input_schema": {
            "type": "object",
            "properties": {"notes": {"type": "string"}},
            "required": ["notes"],
        },
    },
    {
        "name": "set_group_name",
        "description": "Attach a group name to this bill (creates group if needed when members are set).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "update_parsed_bill",
        "description": "Replace parsed bill JSON after user corrections (parse approval stage).",
        "input_schema": {
            "type": "object",
            "properties": {"bill_json": {"type": "object"}},
            "required": ["bill_json"],
        },
    },
    {
        "name": "rerun_bill_parse",
        "description": "Re-run OCR+LLM on the bill image; optional hint for corrections.",
        "input_schema": {
            "type": "object",
            "properties": {"hint": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "rerun_split",
        "description": "Re-run split engine using current parsed bill, members, and notes.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]
