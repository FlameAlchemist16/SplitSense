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

Bill sample:
<img width="250" height="500" alt="image" src="https://github.com/user-attachments/assets/de21d446-5986-4644-b0b8-bf6d28035421" />

OCR Output:

**Format-**
```json
{
  "text": "item_name1(confidence_score) item_name2(confidence_score)",
  "low_confidence_detected": "True/False",
  "confidence_threshold": "threshold_value"
}
```
**Sample** **Output**
```json
{
  "text": "DINE-IN(0.94) Main:Table A4(0.92) Token No113(0.96) Item Name(0.95) Qty(1.0) Rate(1.0) Amt(1.0) DRINKING WATER (1(0.94) LITRE)(1.0) 1(0.13) 20.00(1.0) 20.00(1.0) VEGETABLE NOODLES(0.97) 1(0.39) 280.00(1.0) 280.00(1.0) LASAGNE VEGETARIANA(0.97) 490.00(1.0) 490.00(1.0) SUB TOTAL(0.95) Rs790.00(1.0) TOTAL(1.0) Rs 790.00(0.94) GRAND TOTAL(0.97) Rs790.00(1.0) Tax Summary(0.97) Tax Name(0.94) Taxable Amt(0.96) Tax Amt(0.95) CGST2.5%(0.99) Rs 752.38(0.96) Rs 18.81(0.94) SGST2.5%(0.99) Rs 752.38(0.95) Rs18.81(0.99) (Inclusive of 5% Gst)(0.93) ",
  "low_confidence_detected": "True",
  "confidence_threshold": 0.94
}
```

### 2. Parse
Claude Haiku structures the raw OCR text into a clean JSON list of line items, each with a name, price, and inferred category (`veg`, `non_veg`, `alcohol`, `shared`, `tax`).

```json
{
  "item_details": [
    {
      "item": "DRINKING WATER (1 LITRE)",
      "quantity": 1,
      "price": 20,
      "category": "shared",
      "confidence": 0.97
    },
    {
      "item": "VEGETABLE NOODLES",
      "quantity": 1,
      "price": 280,
      "category": "veg",
      "confidence": 0.79
    },
    {
      "item": "LASAGNE VEGETARIANA",
      "quantity": 1,
      "price": 490,
      "category": "veg",
      "confidence": 0.97
    },
    {
      "item": "CGST 2.5%",
      "quantity": "NULL",
      "price": 18.81,
      "category": "tax",
      "confidence": 0.96
    },
    {
      "item": "SGST 2.5%",
      "quantity": "NULL",
      "price": 18.81,
      "category": "tax",
      "confidence": 0.97
    }
  ],
  "total_validation": {
    "ocr_total": 790,
    "calculated_total": 790,
    "mismatch": "False",
    "note": "Bill is inclusive of 5% GST. Tax amount (37.62) is already included in the grand total of 790.00. Calculated total matches OCR total."
  }
}
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
