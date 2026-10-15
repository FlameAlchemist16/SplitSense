from dataclasses import dataclass, field
from enum import Enum


class Stage(str, Enum):
    INTAKE = "intake"
    PARSE = "parse"
    SPLIT = "split"
    DEBT = "debt"
    COMMIT = "commit"
    DONE = "done"


@dataclass
class WorkflowState:
    stage: Stage = Stage.INTAKE
    image_path: str | None = None
    group_name: str | None = None
    member_ids: list[int] = field(default_factory=list)
    paid_by_id: int | None = None
    notes: str = ""
    currency: str = "INR"
    parsed_bill: dict | None = None
    split_result: dict | None = None
    nets_preview: list[dict] | None = None
    debt_preview: list[dict] | None = None
    committed_bill_id: int | None = None

    def intake_missing(self) -> list[str]:
        missing = []
        if not self.image_path:
            missing.append("bill image path")
        if not self.member_ids:
            missing.append("at least one group member")
        if not self.paid_by_id:
            missing.append("who paid the bill")
        elif self.paid_by_id not in self.member_ids:
            missing.append("payer must be one of the bill members")
        return missing

    def member_names(self, name_by_id: dict[int, str]) -> list[str]:
        return [name_by_id[mid] for mid in self.member_ids if mid in name_by_id]

    def snapshot_for_agent(self, name_by_id: dict[int, str]) -> dict:
        return {
            "stage": self.stage.value,
            "image_path": self.image_path,
            "group_name": self.group_name,
            "member_names": self.member_names(name_by_id),
            "member_ids": self.member_ids,
            "paid_by": name_by_id.get(self.paid_by_id) if self.paid_by_id else None,
            "notes": self.notes,
            "currency": self.currency,
            "intake_complete": len(self.intake_missing()) == 0,
            "intake_missing": self.intake_missing(),
            "has_parsed_bill": self.parsed_bill is not None,
            "has_split_result": self.split_result is not None,
            "has_debt_preview": self.debt_preview is not None,
            "committed_bill_id": self.committed_bill_id,
        }
