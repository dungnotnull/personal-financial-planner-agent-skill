---
name: sub-risk-screener
description: Surface household financial risk red flags - emergency fund, debt-to-income, high-interest debt, insurance gaps, concentration - each tied to a named benchmark and severity.
---

## Purpose
Identify urgent risks before any optimization advice is given. Every flag
names the benchmark it breaches and a severity so the roadmap can order fixes.

## Inputs
The normalized `Ledger` from `sub-profile-intake` plus the `Profile`
(insurance, dependents, asset list).

## Risk checks (canonical implementation: tools/planner_engine.py :: risk_screen)

| Code | Metric | Formula | Benchmark | Severity rule |
|------|--------|---------|-----------|----------------|
| EF | emergency_fund_months | `liquid_assets / essential_monthly_expenses` | 3-6 months (CFPB) | Critical if <1, else High |
| DTI | debt_to_income | `debt_payments / gross_income` | <36% (lender norms) | Medium if 36-43%, High if >43% |
| HID | high_interest_debt | count of debts with APR > high_interest_apr | no APR > region threshold | High (always) |
| INS | insurance_coverage | gaps across health/disability/life/property | no critical gap | High if life gap w/ dependents, else Medium |
| CONC | concentration | `max(holding)/investable_assets` | <40% single asset (MPT) | High |
| CASH | cash_flow | `surplus` | >=0 surplus | Critical when negative |

### Insurance gap decision tree
- health != full -> gap
- disability != full -> gap
- dependents > 0 and life == none -> gap (Critical-leaning)
- property == none and an insurable asset (home/house/car/vehicle) present -> gap

### Concentration scope
Only **non-liquid investment holdings** count toward concentration. A small
checking account is not an investment-concentration concern.

## Severity bands
`Critical > High > Medium > Low`. Critical flags must appear first in the
roadmap (e.g., negative cash flow precedes everything).

## Output
```
[
  {"code": "HID", "metric": "high_interest_debt", "value": 3,
   "benchmark": "no APR >15%", "severity": "High",
   "detail": "3 debt(s) above 15% APR: cardA@24%, cardB@19%, cardD@22%"}
]
```

## Worked example
Debts: cardA 5000@24%, cardB 4000@19%, cardC 5000@16%, cardD 4000@22%;
gross $5,500; min payments sum $520.
- DTI = 520/5500 = 9.5% -> no DTI flag (<36%).
- HID = 3 debts >15% APR (A, B, D) -> High flag.
- Emergency fund: liquid $1000 / essential ($1900 needs + $520 debt) = 0.42 mo
  -> Critical (<1 month).

## Quality Gate
- [ ] Emergency-fund months and DTI both computed when applicable.
- [ ] Each flag names the benchmark it breaches and its severity.
- [ ] Concentration computed over investment (non-liquid) holdings only.
- [ ] Negative cash flow surfaced as Critical.
