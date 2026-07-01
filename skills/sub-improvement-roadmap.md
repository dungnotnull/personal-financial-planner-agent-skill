---
name: sub-improvement-roadmap
description: Produce a prioritized personal-finance action plan ordered by financial-priority logic, each item tagged with effort, impact, framework reference, and structured detail.
---

## Purpose
Turn the scorecard and risk flags into a sequenced, actionable plan.

## Inputs
`Scorecard`, `risk_flags`, `goals`, `Ledger`.

## Priority order (default; tools/planner_engine.py :: roadmap)
1. **Fix negative cash flow** (Critical; nothing else matters while bleeding).
2. **Restructure high-interest debt** - present both avalanche (math-optimal)
   and snowball (behavioral) payoff schedules.
3. **Build emergency fund** to target months (CFPB 3-6).
4. **Capture employer match / tax-advantaged contributions** (educational,
   region-dependent; see tools/regions.json).
5. **Fund time-bound goals** - compute required monthly savings and feasibility.
6. **Diversified long-term investing** - and rebalance over-concentrated
   holdings below the concentration limit first.

## Payoff math (avalanche vs snowball)
For each month until all balances clear (cap 600):
```
balance += balance * APR / 12          # accrue interest
pool = fixed_monthly_payment
for debt in order:
    pay = min(balance, pool); balance -= pay; pool -= pay
    if balance <= 0: record payoff_month
```
- **Avalanche order:** highest APR first, tie-break lowest balance.
- **Snowball order:** smallest balance first, tie-break highest APR.
- `fixed_monthly_payment = max(0, surplus) + savings_expense` (the cash freed
  for debt attack), falling back to the sum of minimums if non-positive.

## Goal feasibility
```
required_monthly = target_amount / (horizon_years * 12)
feasible = monthly_contribution >= required_monthly
```

## Effort / impact rubric
- Effort: `S` (<1 month / configure automation) | `M` (1-3 months / behavior
  change) | `L` (structural / multi-step rebalance).
- Impact: `Low | Med | High`. Cash-flow fix and high-interest debt removal are
  High; on-track goal funding is Med.

## Output (RoadmapItem)
```
{
  "order": 2,
  "action": "Restructure high-interest debt",
  "effort": "M", "impact": "High",
  "framework": "Debt avalanche vs snowball",
  "rationale": "Avalanche is math-optimal; snowball is behavioral.",
  "detail": {
    "avalanche": [{"debt":"cardA","apr":0.24,"payoff_months":48}, ...],
    "snowball":   [{"debt":"cardB","apr":0.19,"payoff_months":30}, ...],
    "monthly_payment": 520.0
  }
}
```

## Worked example (multi_card)
Surplus positive + savings = ~$520/mo freed. Avalanche pays cardA (24%) first;
snowball pays cardB (smallest $4k) first. Both schedules emitted. This item
precedes "Diversified low-cost long-term investing".

## Quality Gate
- [ ] Items follow the financial-priority order (cash flow > debt > emergency
  fund > goals > diversified investing).
- [ ] Each item has effort + impact + framework reference.
- [ ] Debt item emits both avalanche and snowball schedules.
- [ ] Over-concentration produces a rebalance item, never a "growth" reward.
