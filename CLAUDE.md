# CLAUDE.md - Personal Financial Planner Skill (Idea 50)

**Skill name:** `personal-financial-planner`
**Tagline:** Income-tiered budget, savings & basic-investing plan with a graded financial-health scorecard.
**Current phase:** Production-grade complete (Phases 0-5 all done).
**Source idea:** 50 - *Build & evaluate a personal financial plan (budget, savings, basic investing) matched to income level and life goals, grounded in world-renowned personal-finance methods, with improvement recommendations; continuously crawl authoritative papers/docs to stay current.*
**Cluster:** `finance-insurance`

## Problem This Skill Solves
People lack an objective, framework-grounded view of their finances. This skill
ingests income/expenses/debts/goals, screens risk (emergency fund, debt load,
insurance gaps, concentration), scores financial health against named frameworks
(50/30/20, debt-avalanche/snowball, FIRE savings rate, emergency-fund months),
and outputs a prioritized improvement roadmap. **Educational only - not licensed
financial advice.**

## Harness Flow Summary
1. **Intake** (`sub-profile-intake`) - income, fixed/variable expenses, debts, assets, goals, dependents.
2. **Risk screen** (`sub-risk-screener`) - emergency fund, debt-to-income, high-interest debt, insurance gaps, concentration.
3. **Research** (main) - verify current rates/limits vs SECOND-KNOWLEDGE-BRAIN.md and tools/regions.json.
4. **Scoring** (`sub-scoring-engine`) - financial-health scorecard vs frameworks.
5. **Roadmap** (`sub-improvement-roadmap`) - prioritized actions, effort/impact.

## Sub-skills
`sub-profile-intake.md` | `sub-risk-screener.md` | `sub-scoring-engine.md` |
`sub-improvement-roadmap.md`

## Tools Required
WebSearch, WebFetch, Read, Write, Bash.

## Deterministic Engine (canonical calculator)
`tools/planner_engine.py` (pure-stdlib) implements intake -> risk_screen ->
score -> roadmap -> report, applies `tools/regions.json` benchmarks, and ships
six built-in scenarios. The skill invokes it via Bash for auditable, reproducible
figures and narrates results with educational framing.

| Tool | Purpose |
|------|---------|
| `tools/planner_engine.py` | Deterministic scoring/roadmap engine |
| `tools/run_scenarios.py` | Scenario test harness (exit 0 = all pass) |
| `tools/knowledge_updater.py` | Weekly knowledge crawl pipeline |
| `tools/knowledge_sources.json` | Crawl source config |
| `tools/regions.json` | Region localization defaults (US/VN/EU/UK) |

## Knowledge Sources
SSRN (household finance), NBER, CFPB, OECD/World Bank financial-literacy reports,
central-bank rate data, Bogleheads/CFP-board educational materials.

## Test Fixtures
`tests/test_scenarios.json` (machine-readable) + `tests/test-scenarios.md`
(descriptions). `python tools/run_scenarios.py` validates all six scenarios.

## Quality Gates
- Cash flow reconciles (surplus computed or deficit flagged).
- Every scorecard metric cites a named, dated benchmark.
- Roadmap ordered by financial-priority logic (cash flow > debt > emergency
  fund > goals > diversified investing).
- Educational disclaimer present in every report.
- Offline/degraded mode explicitly flagged.
- Region benchmarks applied and noted.

## Active Development Tasks
- [x] Scaffold deliverables.
- [x] Localize rate/tax assumptions per region (`tools/regions.json`).
- [x] Canonical deterministic engine + scenario harness.
- [x] Robust weekly knowledge pipeline (stdlib fallback).
- [x] Open-source readiness (README, LICENSE, schemas).

## Reference Docs
PROJECT-detail.md | PROJECT-DEVELOPMENT-PHASE-TRACKING.md |
SECOND-KNOWLEDGE-BRAIN.md | README.md
