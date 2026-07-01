---
name: sub-scoring-engine
description: Produce a financial-health scorecard scoring each metric against a named, dated benchmark and rolling up to a 0-100 weighted total with a verdict band.
---

## Purpose
Convert the ledger + risk flags into a defensible 0-100 financial-health
scorecard. Every metric cites its benchmark and source.

## Inputs
`Ledger`, `Profile`, `risk_flags`, and region benchmarks from
`tools/regions.json` (applied by `planner_engine.configure(region)`).

## Dimensions & Weights
| Metric | Weight | Benchmark | Source |
|--------|--------|-----------|--------|
| Emergency fund | 20% | 3-6 months | CFPB |
| Debt load (DTI + high-interest) | 25% | DTI <36%, no APR >15% | Lender norms / CFPB |
| Savings rate | 20% | >=20% of take-home | 50/30/20 / FIRE |
| Budget balance | 15% | 50/30/20 split | Warren & Tyagi |
| Insurance coverage | 10% | no critical gap | Risk-mgmt basics |
| Investment diversification | 10% | not over-concentrated | MPT / Bogleheads |

## Per-metric scoring (piecewise-linear, tools/planner_engine.py :: score)
- **emergency_fund**: `lin(ef_months, 0->0, 6mo->100)`.
- **debt_load**: `0.6 * dti_score + 0.4 * hi_score`, where
  `dti_score = 100 - lin(dti, 0->0, 0.43->100)` and
  `hi_score = 100 if no high-interest debt else max(0, 100 - 30*count)`.
- **savings_rate**: `lin(savings_rate, 0->0, 20%->100)`, where
  `savings_rate = (savings_expense + max(0, surplus)) / take_home`.
- **budget_balance**: `100 * (1 - deviation)`, where
  `deviation = (|needs%-50%| + |wants%-30%| + |savings%-20%|) / 2`.
- **insurance**: `100` if no INS flag, else `max(0, 100 - 25*flag_count)`.
- **diversification**: `100` if no CONC flag, else `max(0, 100 - 40*flag_count)`.
  Over-concentration is **never** rewarded as growth.

## Verdict bands
`total = clamp(sum(weight*score), 0, 100)`.
- `>=80` Healthy
- `60-79` Stabilizing
- `<60` Fragile

## Output (Scorecard)
```
{
  "metrics": [
    {"name":"debt_load","weight":0.25,"value":0.095,
     "benchmark":"DTI <36%, no APR >15%","score":62.0,
     "source":"Lender norms / CFPB","rationale":"DTI 9.5%; 3 high-interest debt(s)."}
  ],
  "total": 60.1, "verdict": "Stabilizing", "band": "stabilizing"
}
```

## Worked example (multi_card scenario)
DTI 9.5% -> dti_score ~78; 3 high-interest debts -> hi_score = max(0,100-90)=10;
debt_score = 0.6*78 + 0.4*10 = 50.8 -> contribution 0.25*50.8 = 12.7.
Savings rate ~0 -> savings_score 0. Total lands in Stabilizing band.

## Quality Gate
- [ ] Every metric cites a named benchmark and source.
- [ ] Total weighted from the six metrics only; reflects risk-flag severity.
- [ ] Concentration never inflates the diversification score.
- [ ] Verdict band derived from total per the bands above.
