# SplitSense

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Phase](https://img.shields.io/badge/phase-1%20CLI-complete-green.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

AI-assisted bill splitting: scan a receipt, split by diet and alcohol rules, confirm each step, then persist balances in SQLite.

**Stack:** PaddleOCR · Claude Haiku · SQLAlchemy · SQLite

---

## What Phase 1 includes

| Area | Status |
|------|--------|
| OCR + LLM bill parsing | Done |
| Split engine + NL overrides | Done |
| Debt simplification + settlements | Done |
| Interactive agent (ReAct + staged approval) | Done |
| One-shot CLI for scripts / admin | Done |
| Streamlit dashboard | Not started |
| Discord bot | Planned (next) |
| FastAPI + React + Docker | Later |

**Pipeline**

```
intake → parse → split → debt preview → save to SQLite
         ↑ human approve at each boxed stage (interactive mode)
```

---

## Quick start

```bash
cd splitsense
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
copy .env.example .env         # Windows; use cp elsewhere
```

Edit `.env`:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Required for agent + bill parsing |
| `LLM_MODEL` | e.g. `claude-haiku-4-5-20251001` |
| `DATABASE_URL` | Default `sqlite:///splitsense.db` |
| `OCR_MODEL` | Optional PaddleOCR version override |

### Interactive agent (recommended)

```bash
python -m agent.core
```

1. **Intake** — Chat with the agent to set the bill image, members (or load a group), create missing people, payer, and notes. Type **`proceed`** when ready.
2. **Parse** — OCR + structured items. **`a`** approve · **`r`** revise · **`j`** JSON · **`q`** quit.
3. **Split** — Per-person amounts and warnings (same keys).
4. **Debts** — Net balances including this bill + simplified “who pays whom” (preview only until saved).
5. **Commit** — Writes bill and splits; updates stored balances.

### Admin commands (no approval gates)

```bash
python -m agent.core people add --name Raj --diet veg
python -m agent.core people list
python -m agent.core split --bill path/to/bill.jpg --people "Raj, Rahul" --paid-by Raj --notes "Rahul skips alcohol"
python -m agent.core bills
python -m agent.core balances
python -m agent.core debts
python -m agent.core settle --from Rahul --to Raj --amount 200
```

Shorthand (same as `split`): `python -m agent.core --bill bill.jpg --people "Raj, Rahul"`

### Tests

```bash
python -m pytest
```

Unit tests cover split rules, debt simplification, CRUD, and workflow state. OCR/API scripts live under `tests/manual_*.py` (run manually with a real bill and API key).

---

## Split logic (summary)

1. Natural-language overrides (Haiku → include / exclude / replace).
2. Category assignment — veg, non-veg, alcohol, shared, tax.
3. Proportional tax on each person’s pre-tax share.
4. Equal split within each item’s eligible group.

---

## Project layout

```
splitsense/
├── agent/
│   ├── core.py              # Entry point
│   ├── orchestrator.py      # Staged workflow + approvals
│   ├── react_loop.py        # ReAct tool loop (Anthropic)
│   ├── agent_tools.py       # Tool definitions + runner
│   ├── commands.py          # Admin / one-shot CLI
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

- [x] Phase 1 — CLI agent, SQLite, staged human verification
- [ ] **Phase 3 (next)** — Discord bot for group chats (requirements and deployment plan TBD with you before build)
- [ ] Phase 2 — Streamlit dashboard (optional; may follow Discord)
- [ ] Phase 4 — FastAPI backend, web UI, containerized deploy

---

## Upcoming: Discord + real-world deploy

Not implemented yet. Before coding, we will align on:

- Bot flows (upload bill in channel, map Discord users → `People`, approvals in-thread or DMs).
- Hosting (always-on process vs serverless; where OCR runs).
- Secrets (`DISCORD_TOKEN`, Anthropic key), database (SQLite vs managed Postgres for multi-user).
- How Phase 1 Python modules are reused vs a thin Discord adapter.

Say when you want to walk through that plan; Phase 1 is the foundation the bot will call into.

---

## Author

**Mridul Khare** — [mridulkhr4@gmail.com](mailto:mridulkhr4@gmail.com) · [LinkedIn](https://linkedin.com/in/mridul-khare)

## License

[MIT](LICENSE) — Copyright (c) 2025 Mridul Khare
