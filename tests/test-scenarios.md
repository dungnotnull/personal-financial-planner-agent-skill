# Test Scenarios - Personal Financial Planner (Idea 50)

Machine-readable fixtures live in `tests/test_scenarios.json`; the automated
harness is `tools/run_scenarios.py`. Run:
```
python tools/run_scenarios.py            # human-readable pass/fail
python tools/run_scenarios.py --json     # machine-readable
```
Expected result: `ALL PASSED` (exit code 0). No network, no models.

## Scenario 1 - Low income, tight budget
- **Input:** $2,500/mo net, rent $1,100, no savings, no debt, $200 liquid.
- **Expected:** EF + INS risk flags; roadmap includes emergency-fund build and
  diversified investing; scorecard cites benchmarks; disclaimer present.
- **Engine result:** score ~70.7 (Stabilizing).
- **Pass:** scorecard cites benchmarks; roadmap contains emergency-fund item.

## Scenario 2 - Multi-card debt
- **Input:** 4 cards, APRs 24%/19%/16%/22%, total $18k; gross $5,500.
- **Expected:** HID flag; roadmap debt item emits both avalanche and snowball
  payoff schedules; debt precedes investing.
- **Engine result:** score ~60.1 (Stabilizing).
- **Pass:** both payoff methods emitted and populated; priority order respected.

## Scenario 3 - House-savings goal
- **Input:** $6k/mo net, $60k down-payment target in 5y, contributing $800/mo.
- **Expected:** required monthly savings computed; feasibility flagged;
  educational framing maintained.
- **Engine result:** score ~91.2 (Healthy).
- **Pass:** `required_monthly` computed; `feasible` boolean set.

## Scenario 4 - Negative cash flow (urgent)
- **Input:** $3,700 net; expenses total $4,000 -> $300/mo deficit.
- **Expected:** CASH flag at Critical severity; roadmap item 1 is the cash-flow
  fix; no investing item precedes it.
- **Engine result:** score ~55.1 (Fragile).
- **Pass:** Critical CASH flag; cash-flow fix is roadmap item 1.

## Scenario 5 - Over-concentrated crypto
- **Input:** 80% of investable assets in one token (TOKENX); no emergency fund.
- **Expected:** CONC + EF flags; diversification metric not rewarded as growth;
  rebalance roadmap item present.
- **Engine result:** score ~70.5 (Stabilizing); diversification score <80.
- **Pass:** concentration flagged; rebalance item emitted.

## Scenario 6 - Offline / degraded mode
- **Input:** normal profile; WebSearch unavailable (`offline=true`).
- **Expected:** `offline_mode=true`; `offline_limitation_flagged` gate true;
  all sources dated; brain-based benchmarks used.
- **Engine result:** score ~76.8; offline_mode=true.
- **Pass:** offline limitation explicitly stated and gated.
