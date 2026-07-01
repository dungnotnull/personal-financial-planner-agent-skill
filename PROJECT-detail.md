# PROJECT-detail.md - Personal Financial Planner (Idea 50)

## Executive Summary
A harness skill that ingests a household's financial picture, screens risk,
scores financial health against named personal-finance frameworks, and emits a
prioritized improvement roadmap. Educational, not licensed advice.

## Problem Statement
Individuals manage money ad hoc, lacking benchmarks (emergency-fund months,
debt-to-income, savings rate). This skill provides an objective scorecard and a
concrete, prioritized plan, grounded in named frameworks and computed
deterministically by `tools/planner_engine.py`.

## Target Users & Use Cases
- **Early-career earner:** "I make $3k/mo, how should I budget?" -> 50/30/20
  plan + savings targets.
- **Debt-burdened household:** "I have 4 cards" -> avalanche vs snowball
  comparison + payoff schedule.
- **Goal planner:** "Save for a house in 5 years" -> savings-rate and
  allocation roadmap.

## Harness Architecture
```
/personal-financial-planner
  -> sub-profile-intake     (income/expenses/debt/goals)    [gate: cash-flow reconciles]
  -> sub-risk-screener      (emergency fund, DTI, insurance)[gate: red flags + severity]
  -> [main] research        (verify rates/limits)           [gate: figures cited/dated]
  -> sub-scoring-engine     (financial-health scorecard)    [gate: each metric vs benchmark]
  -> sub-improvement-roadmap(prioritized actions)           [gate: effort/impact each]
  -> [main] synthesize + disclaimer
```

## Full Sub-Skill Catalog
| Sub-skill | Purpose | Inputs | Outputs | Tools | Gate |
|-----------|---------|--------|---------|-------|------|
| sub-profile-intake | Capture finances/goals | income, expenses, debts, assets, goals | normalized ledger | Read/Bash | Cash flow reconciles |
| sub-risk-screener | Surface risk red flags | ledger, profile | risk flags + severity | Read/Bash | EF + DTI computed |
| sub-scoring-engine | Score financial health | ledger, flags, benchmarks | scorecard 0-100 | Read/Bash | Each metric vs named benchmark |
| sub-improvement-roadmap | Prioritized plan | scorecard, flags, goals | roadmap | Bash | Effort/impact each item |

## Skill File Format Specification
Frontmatter `name`/`description`; sections per Claude skill standard. See
`skills/main.md`.

## E2E Execution Flow
1. Intake reconciles income vs expenses+savings+debt.
2. Risk screen computes emergency-fund months, debt-to-income, high-interest-debt
   flag, insurance/coverage gaps, concentration.
3. Research verifies current savings/loan rates and contribution limits.
4. Scoring produces the health scorecard.
5. Roadmap prioritizes (high-interest debt -> emergency fund -> goal savings ->
   diversified investing).
6. Output with mandatory educational disclaimer.

Error handling: negative cash flow -> Critical flag; crypto/leveraged exposure
-> concentration risk note (not rewarded as growth); offline -> use brain + flag.

## SECOND-KNOWLEDGE-BRAIN Integration
Sources: SSRN household finance, NBER, CFPB, OECD/World Bank, central-bank
rates. Append scored, deduplicated entries weekly via
`tools/knowledge_updater.py`.

## Supporting Tools Spec
- `tools/planner_engine.py`: deterministic intake/risk/score/roadmap engine
  (pure stdlib; region-aware via `tools/regions.json`).
- `tools/run_scenarios.py`: scenario test harness (exit 0 = all pass).
- `tools/knowledge_updater.py`: weekly crawl pipeline, SHA1-hash dedup.
- `tools/knowledge_sources.json`: crawl source config.
- `tools/regions.json`: region localization defaults (US/VN/EU/UK).

## Quality Gates
- Each scored metric compared to a named benchmark with a dated source.
- Roadmap ordered by financial-priority logic (cash flow > debt > emergency
  fund > goals > diversified investing).
- Educational disclaimer always present.
- Offline mode flagged.
- Region benchmarks applied and noted.

## Test Scenarios (summary)
1. Low income tight budget. 2. Multi-card debt avalanche/snowball.
3. House-savings goal. 4. Negative cash flow (urgent). 5. Over-concentrated
   crypto. 6. Offline/degraded mode. (Full set in tests/.)

## Key Design Decisions
1. Never give licensed/individualized investment advice - educational framing.
2. High-interest debt prioritized before investing.
3. Emergency fund is a first-class risk metric.
4. All rate figures dated.
5. Region note for tax/limits (`tools/regions.json`).
6. Deterministic engine for auditable, reproducible output regardless of model
   variance.
