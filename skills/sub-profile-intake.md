---
name: sub-profile-intake
description: Capture and reconcile a household's income, expenses, debts, assets, and goals into a normalized ledger for downstream risk-screening and scoring.
---

## Purpose
Build a complete, reconciled financial picture before any scoring or advice.
The output ledger is the single input contract for the risk screener, scoring
engine, and roadmap.

## Inputs (Profile JSON schema)
```json
{
  "region": "US",
  "monthly_income_gross": 5500.0,
  "monthly_income_net": 4500.0,
  "expenses": [
    {"name": "rent", "amount": 1200.0, "category": "needs"},
    {"name": "dining", "amount": 300.0, "category": "wants"},
    {"name": "sinking_fund", "amount": 500.0, "category": "savings"}
  ],
  "debts": [
    {"name": "cardA", "balance": 5000.0, "apr": 0.24, "min_payment": 150.0}
  ],
  "assets": [
    {"name": "savings", "value": 1000.0, "liquid": true},
    {"name": "TOKENX", "value": 80000.0, "liquid": false}
  ],
  "goals": [
    {"name": "house_down_payment", "target_amount": 60000.0,
     "horizon_years": 5.0, "monthly_contribution": 800.0}
  ],
  "dependents": 0,
  "insurance": {"health": "full", "disability": "none", "life": "none", "property": "none"},
  "note": ""
}
```
- `category` is one of `needs | wants | savings`; unknown categories default to
  `needs` (conservative).
- `apr` is a fraction (0.24 = 24% APR).
- `liquid` marks cash-like assets usable for the emergency fund.

## Process
1. Categorize every expense into needs / wants / savings; sum each bucket.
2. Compute debt service = sum of `min_payment` across all debts.
3. Compute `liquid_assets` = sum of liquid asset values;
   `investable_assets` = sum of **non-liquid** asset values (investment holdings).
4. `essential_monthly_expenses = needs + debt_payments` (what an emergency fund
   must cover, per CFPB framing).
5. `take_home = monthly_income_net or monthly_income_gross`.
6. Reconcile: `surplus = take_home - needs - wants - savings_expense - debt_payments`.
7. If `surplus < 0`, flag the deficit explicitly (downstream treats it Critical).
8. Flag missing essentials: no rent/housing line, no insurance line, no
   emergency-fund assets.

## Output Ledger (Ledger)
```
{
  "region", "monthly_income_gross", "monthly_income_net",
  "needs", "wants", "savings_expense",
  "debt_payments", "liquid_assets", "investable_assets",
  "essential_monthly_expenses", "goals[]",
  "surplus", "reconciliation_note"
}
```

## Canonical implementation
`tools/planner_engine.py :: intake(profile) -> Ledger`.
Run: `python tools/planner_engine.py path/to/profile.json --json`.

## Worked example
Net $2,500; needs $1,650 (rent 1100 + groceries 400 + utilities 150), wants
$30, savings $0, no debt, liquid $200.
`essential = 1650 + 0 = 1650`; `surplus = 2500 - 1650 - 30 - 0 - 0 = 820`.
Note: "cash flow reconciled with surplus".

## Quality Gate
- [ ] Cash flow reconciles (surplus computed; deficit explicitly flagged).
- [ ] Every debt carries `apr` + `min_payment`.
- [ ] Liquid vs investable assets distinguished (emergency fund uses liquid only).
- [ ] Unknown expense categories defaulted to `needs` and noted.
