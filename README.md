# SplitSense

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Phase](https://img.shields.io/badge/phase-1%20CLI-complete-green.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

SplitSense parses restaurant bills from images, applies dietary and alcohol-aware splitting rules, and stores balances in SQLite. The default interface is an interactive CLI agent with human confirmation at parse, split, and debt-preview stages.

| Component | Technology |
|-----------|------------|
| OCR | PaddleOCR |
| Structuring & overrides | Claude Haiku (Anthropic API) |
| Persistence | SQLite, SQLAlchemy |
| Orchestration | ReAct tool loop + staged workflow |

---

## Current release (Phase 1)

| Capability | Status |
|------------|--------|
| Bill image → OCR → structured line items | Available |
| Split engine (categories, tax, NL overrides) | Available |
| Debt simplification and settlement records | Available |
| Interactive agent with staged approval | Available |
| One-shot admin CLI (`split`, `people`, `balances`, …) | Available |

### Processing pipeline (interactive mode)

```
intake → parse → split → debt preview → commit to database
              ↑ user approval after parse, split, and debt preview
```

**Intake (ReAct):** Bill image path, participants (names or existing group), payer, optional split notes. Missing people can be registered in the database. Continue with `proceed` when intake is complete.

**Parse:** OCR and LLM produce `item_details` plus total validation metadata.

**Split:** Assigns amounts per person; warnings for unknown categories or empty eligibility.

**Debt preview:** Net balances including the pending bill and a simplified payment list. No database write until commit.

**Commit:** Inserts bill and split rows; balances reflect the new bill.

### Split rule order

1. Natural-language overrides (`include` / `exclude` / `replace` via LLM).
2. Category rules: `veg`, `non_veg`, `alcohol`, `shared`, `tax`.
3. Proportional tax from each person’s pre-tax subtotal.
4. Equal division among eligible people per line item.

---

## Installation

```bash
git clone https://github.com/MridulKhare/splitsense
cd splitsense
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
copy .env.example .env         # Windows; use cp on other platforms
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `LLM_MODEL` | Yes | Model id (e.g. `claude-haiku-4-5-20251001`) |
| `DATABASE_URL` | Yes | Default: `sqlite:///splitsense.db` |
| `OCR_MODEL` | No | PaddleOCR version override |

---

## Usage

### Interactive agent

```bash
python -m agent.core
```

| Stage | User actions |
|-------|----------------|
| Intake | Chat; type `proceed` when ready |
| Parse / split / debts | `a` approve, `r` revise (agent), `j` show JSON, `q` quit |
| Revision | Describe changes; type `done` to return to approval |

### Admin CLI

Commands run the pipeline or database operations without approval gates.

```bash
python -m agent.core people add --name Raj --diet veg
python -m agent.core people list
python -m agent.core split --bill path/to/bill.jpg --people "Raj, Rahul" --paid-by Raj
python -m agent.core bills
python -m agent.core balances
python -m agent.core debts
python -m agent.core settle --from Rahul --to Raj --amount 200
```

Equivalent split shorthand:

```bash
python -m agent.core --bill bill.jpg --people "Raj, Rahul"
```

---

## Testing

```bash
python -m pytest
```

Automated tests cover the split engine, debt simplifier, CRUD flows, and workflow state. Scripts under `tests/manual_*.py` require a local bill image and API credentials for end-to-end OCR and LLM checks.

---

## Repository layout

```
splitsense/
├── agent/
│   ├── core.py              # CLI entry
│   ├── orchestrator.py      # Staged workflow
│   ├── react_loop.py        # Anthropic tool-use loop
│   ├── agent_tools.py       # Agent tools
│   ├── commands.py          # Admin commands
│   ├── workflow_state.py
│   ├── cli_display.py
│   ├── llm_client.py
│   ├── prompts.py
│   └── tools/
│       ├── bill_parser.py
│       ├── split_engine.py
│       └── debt_simplifier.py
├── db/
│   ├── models.py
│   └── crud.py
├── tests/
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## Roadmap

| Phase | Scope | Status |
|-------|--------|--------|
| 1 | CLI agent, SQLite, staged verification | Complete |
| 2 | Discord bot | Planned |

---

## Author

**Mridul Khare** — [mridulkhr4@gmail.com](mailto:mridulkhr4@gmail.com) · [LinkedIn](https://linkedin.com/in/mridul-khare)

## License

[MIT](LICENSE) — Copyright (c) 2025 Mridul Khare
