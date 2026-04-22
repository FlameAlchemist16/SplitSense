# SplitSense 🧾

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-in%20development-orange.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

**AI-powered bill splitting agent** — scan a receipt, describe who was present, and get a fair split in seconds. No manual item entry. No "everyone pays equally" nonsense.

> Built with PaddleOCR + Claude Haiku + SQLite. Dietary rules, alcohol splits, and debt simplification — all handled automatically.

---

## The problem

Every group dinner ends the same way: someone photographs the bill, someone else opens a calculator, and someone argues about who had what. It's slow, error-prone, and unfair — the vegans subsidise the steak, the non-drinkers pay for the beer.

SplitSense automates the entire pipeline:

```
scan → parse → reason → split → track
```

---

## How it works

### 1. Scan
Point it at a bill photo. PaddleOCR extracts raw text from the image — no manual entry.

### 2. Parse
Claude Haiku structures the raw OCR text into a clean JSON list of line items, each with a name, price, and inferred category (`veg`, `non_veg`, `alcohol`, `shared`, `tax`).

```json
[
  { "item": "Paneer Tikka",   "price": 320, "category": "veg"     },
  { "item": "Chicken Biryani","price": 450, "category": "non_veg" },
  { "item": "Beer x4",        "price": 600, "category": "alcohol" },
  { "item": "Bread Basket",   "price": 150, "category": "shared"  },
  { "item": "Service Charge", "price": 152, "category": "tax"     }
]
```

### 3. Split
The split engine applies rules in priority order:

| Priority | Rule |
|----------|------|
| 1 | Explicit prompt override (`"Rahul is skipping alcohol tonight"`) |
| 2 | Category rule — veg items → veg people, alcohol → drinkers only |
| 3 | Proportional tax/service charge based on each person's subtotal |
| 4 | Equal split for shared/unclassifiable items |

### 4. Track
Splits, balances, and settlement status are persisted in SQLite. A debt simplification algorithm collapses cross-debts to minimise total transactions.

```
Before: A owes B ₹200 · B owes C ₹200 · C owes A ₹100  →  3 transactions
After:  A owes C ₹100 · A owes B ₹100                   →  2 transactions
```

---

## Features

- **Bill scanning** — PaddleOCR (local, free) for image-to-text
- **LLM structuring** — Claude Haiku parses messy OCR into clean JSON
- **Dietary splitting** — veg / non-veg / alcohol / shared category logic
- **People profiles** — persistent diet and drinking preferences per person
- **Prompt overrides** — natural language rules applied on top of defaults
- **Debt simplification** — greedy graph reduction across all open bills
- **Settlement tracking** — mark payments, partial or full

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| LLM | Claude Haiku (Anthropic API) |
| OCR | PaddleOCR |
| Backend | Python + FastAPI (Phase 4) |
| Database | SQLite → PostgreSQL |
| ORM | SQLAlchemy + Alembic |
| Dashboard | Streamlit (Phase 2) |
| Agent pattern | ReAct loop with tool calling |

---

## Project structure

```
splitsense/
├── agent/
│   ├── core.py              # Main ReAct agent loop
│   ├── tools/
│   │   ├── bill_parser.py   # PaddleOCR + Haiku structuring
│   │   ├── split_engine.py  # Dietary split logic
│   │   └── debt_simplifier.py
│   └── prompts.py           # System prompt templates
├── db/
│   ├── models.py            # SQLAlchemy models
│   ├── crud.py              # DB read/write helpers
│   └── migrations/          # Alembic migration files
├── dashboard/
│   └── app.py               # Streamlit dashboard (Phase 2)
├── tests/
├── .env                     # ANTHROPIC_API_KEY, DB_URL
├── requirements.txt
└── README.md
```

---

## Roadmap

- [x] Project spec and architecture design
- [ ] **Phase 1** — CLI: OCR pipeline + split engine + SQLite *(in progress)*
- [ ] **Phase 2** — Streamlit dashboard: balances, history, settlements
- [ ] **Phase 3** — Discord bot: split bills directly in group chat
- [ ] **Phase 4** — FastAPI backend + React UI + Docker

---

## Getting started

> Phase 1 (CLI) is currently in development. Setup instructions will be added once the core pipeline is stable.

```bash
# Coming soon
git clone https://github.com/MridulKhare/splitsense
cd splitsense
pip install -r requirements.txt
cp .env.example .env   # Add your ANTHROPIC_API_KEY
python -m agent.core --bill bill.jpg --people "Mridul, Rahul, Priya" --notes "Priya doesn't drink"
```

---

## Why this exists

Most bill splitting tools are dumb calculators — they require manual item entry, apply no dietary logic, and forget everything after you close the app. SplitSense is an intelligent agent: it reads, reasons, and remembers.

The core insight: **vision + LLM reasoning + persistent memory**.

---

## Author

**Mridul Khare** — Data Engineer at Deloitte USI, building towards AI Engineering.
Reach me at [mridulkhr4@gmail.com](mailto:mridulkhr4@gmail.com) · [LinkedIn](https://linkedin.com/in/mridul-khare)

---

## License

Copyright (c) 2025 Mridul Khare

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
You are free to use, copy, and modify this code, but the copyright notice and this permission notice must be included in all copies or substantial portions of the software.
