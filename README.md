# Personal Financial Planner (Idea 50)

> Build & evaluate a personal financial plan (budget, savings, basic investing)
> matched to income level and life goals, grounded in world-renowned
> personal-finance methods, with a prioritized improvement roadmap and a graded
> financial-health scorecard. **Educational only - not licensed financial,
> tax, or investment advice.**

Cluster: `finance-insurance`.

## What it does
A harness skill that ingests a household's financial picture, screens risk,
scores financial health against named personal-finance frameworks (50/30/20,
debt avalanche/snowball, emergency-fund months, DTI, FIRE savings rate, MPT
diversification), and emits a prioritized improvement roadmap. Every benchmark
is named, dated, and traceable to an authoritative source.

```
sub-profile-intake  ->  sub-risk-screener  ->  [research]  ->
sub-scoring-engine  ->  sub-improvement-roadmap  ->  synthesize + disclaimer
```

## Repository layout
```
.
+- CLAUDE.md                         # skill overview / harness summary
+- PROJECT-detail.md                 # full project spec
+- PROJECT-DEVELOPMENT-PHASE-TRACKING.md
+- SECOND-KNOWLEDGE-BRAIN.md          # self-improving knowledge base
+- skills/
|   +- main.md                       # orchestrator skill
|   +- sub-profile-intake.md
|   +- sub-risk-screener.md
|   +- sub-scoring-engine.md
|   +- sub-improvement-roadmap.md
+- tools/
|   +- planner_engine.py             # deterministic engine (stdlib only)
|   +- run_scenarios.py              # scenario test harness
|   +- knowledge_updater.py          # weekly knowledge crawl pipeline
|   +- knowledge_sources.json        # crawl source config
|   +- regions.json                  # region localization defaults
+- tests/
    +- test-scenarios.md             # scenario descriptions
    +- test_scenarios.json           # machine-readable fixtures
```

## Quick start
Requires Python 3.10+. No third-party dependencies for the engine/harness;
`knowledge_updater.py` optionally uses `requests` (falls back to urllib).

```bash
# Run a built-in scenario and print a human-readable report
python tools/planner_engine.py --scenario crypto

# Emit a machine-readable JSON report
python tools/planner_engine.py --scenario multi_card --json

# Assess your own profile
python tools/planner_engine.py path/to/profile.json --json

# Run the full scenario test suite (exit 0 = all pass)
python tools/run_scenarios.py

# Update the knowledge base (weekly cron; --dry-run to preview)
python tools/knowledge_updater.py --dry-run
```

## Profile input schema
See `skills/sub-profile-intake.md`. Minimal example:
```json
{
  "region": "US",
  "monthly_income_gross": 5500, "monthly_income_net": 4500,
  "expenses": [
    {"name": "rent", "amount": 1200, "category": "needs"},
    {"name": "dining", "amount": 300, "category": "wants"}
  ],
  "debts": [{"name": "cardA", "balance": 5000, "apr": 0.24, "min_payment": 150}],
  "assets": [{"name": "savings", "value": 1000, "liquid": true}],
  "goals": [{"name": "house", "target_amount": 60000, "horizon_years": 5,
             "monthly_contribution": 800}],
  "dependents": 0,
  "insurance": {"health": "full", "disability": "none", "life": "none",
                "property": "none"}
}
```

## Scorecard
| Metric | Weight | Benchmark | Source |
|--------|--------|-----------|--------|
| Emergency fund | 20% | 3-6 months | CFPB |
| Debt load (DTI + high-interest) | 25% | DTI <36%, no APR >15% | Lender norms / CFPB |
| Savings rate | 20% | >=20% of take-home | 50/30/20 / FIRE |
| Budget balance | 15% | 50/30/20 split | Warren & Tyagi |
| Insurance coverage | 10% | no critical gap | Risk-mgmt basics |
| Diversification | 10% | not over-concentrated | MPT / Bogleheads |

Verdict bands: >=80 **Healthy**, 60-79 **Stabilizing**, <60 **Fragile**.

## Region localization
`tools/regions.json` carries per-region benchmark overrides (US, VN, EU, UK).
The engine applies them automatically based on `Profile.region`; unknown
regions fall back to US defaults. Tax/limit figures are educational and must be
verified against current law.

## Knowledge pipeline
`tools/knowledge_updater.py` crawls CFPB, NBER, SSRN, OECD weekly, scores
candidates by keyword relevance, dedupes by `<!--h:hash-->` markers, and appends
a dated block to `SECOND-KNOWLEDGE-BRAIN.md`. Schedule via cron.

## Quality gates
- Cash flow reconciles (surplus computed or deficit flagged).
- Every scorecard metric cites a named, dated benchmark.
- Roadmap ordered by financial-priority logic.
- Educational disclaimer present in every report.
- Offline/degraded mode explicitly flagged.
- Region benchmarks applied and noted.

## Disclaimer
This project provides educational information only. It is not individualized,
licensed financial, tax, or investment advice. Consult qualified professionals
before making financial decisions.

## License
MIT - see `LICENSE`.
