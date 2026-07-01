# SECOND-KNOWLEDGE-BRAIN.md - Personal Financial Planner (Idea 50)

Self-improving knowledge base, grown weekly by `tools/knowledge_updater.py`.
Every benchmark below is named, dated, and traceable to an authoritative source.
Educational only - not licensed financial, tax, or investment advice.

## Core Concepts & Frameworks

### Budgeting
- **50/30/20 rule:** 50% needs / 30% wants / 20% savings & debt paydown.
  Source: Warren & Tyagi, *All Your Worth: The Ultimate Lifetime Money Plan* (2005).
- **Zero-based budgeting:** every dollar assigned a job (needs, wants, saving, debt).
  Source: CFPB budget guidance (consumerfinance.gov).
- **Pay-yourself-first / automation:** route savings before discretionary spend.
  Source: Behavioral-finance literature; CFPB automation guidance.

### Emergency preparedness
- **Emergency fund:** 3-6 months of essential expenses.
  Essential expenses = needs + minimum debt service (the runway the fund must
  cover). Source: CFPB (consumerfinance.gov).
  Formula: `emergency_fund_months = liquid_savings / essential_monthly_expenses`.

### Debt management
- **Debt avalanche:** pay highest-APR balance first - mathematically optimal,
  minimizes total interest paid. Payoff modeled by amortizing each debt monthly
  with `interest = balance * APR / 12`, applying a fixed monthly payment in
  APR-descending order.
- **Debt snowball:** pay smallest balance first - behaviorally optimal,
  maximizes early wins and adherence (Gal et al., 2016, SSRN).
- **Debt-to-income (DTI):** `total_monthly_debt_payments / gross_monthly_income`.
  Healthy <36%; mortgage front-end ratio <28%. Source: lender underwriting norms.
- **High-interest debt threshold:** APR > ~15% flagged for priority payoff.
  Source: consumer-finance norms.

### Savings & independence
- **FIRE savings rate:** share of take-home saved. Higher rate -> shorter
  time-to-independence. Context: Trinity study (Cooley et al., 1998) 4% rule.
  Formula: `savings_rate = (savings_expense + max(0, surplus)) / take_home`.
- **Sinking funds:** time-bound goal accounts (house down payment, car, etc.).
  Formula: `required_monthly = target_amount / (horizon_years * 12)`.

### Investing (educational)
- **Diversification / low-cost index investing:** Modern Portfolio Theory
  (Markowitz, 1952); Bogleheads educational principles.
- **Concentration risk:** single asset > ~40% of investable (non-liquid)
  assets is flagged. Concentration is risk, not growth.

## Scoring Dimensions (this skill)

| Metric | Weight | Benchmark | Source |
|--------|--------|-----------|--------|
| Emergency-fund months | 20% | 3-6 months | CFPB |
| Debt load (DTI + high-interest) | 25% | DTI <36%, no APR >15% | Lender norms / CFPB |
| Savings rate | 20% | >=20% of take-home | 50/30/20 / FIRE |
| Budget balance (needs/wants/savings) | 15% | 50/30/20 split | Warren & Tyagi |
| Insurance coverage | 10% | no critical gap | Risk-mgmt basics |
| Investment diversification | 10% | not over-concentrated | MPT / Bogleheads |

Scoring is piecewise-linear per metric, weighted to a 0-100 total, then banded:
>=80 **Healthy**, 60-79 **Stabilizing**, <60 **Fragile**.

## Key Research Papers

| Title | Authors | Year | Venue | Link | Relevance |
|-------|---------|------|-------|------|-----------|
| Financial literacy and planning readiness | Lusardi & Mitchell | 2014 | JEL / NBER | nber.org | Literacy -> better outcomes |
| Optimal debt repayment: avalanche vs snowball | Gal, McShane & Wong | 2016 | SSRN | ssrn.com | Snowball can beat avalanche behaviorally |
| Portfolio Selection | Markowitz | 1952 | Journal of Finance | jstor.org | Modern Portfolio Theory |
| Trinity study (withdrawal rates) | Cooley, Hubbard & Walz | 1998 | AAII | aaii.com | 4% rule context |

## State-of-the-Art Methods & Tools
Zero-based budgeting; sinking funds; automated transfers; tax-advantaged
account sequencing (educational, region-dependent). Region defaults are
maintained in `tools/regions.json` and applied by `tools/planner_engine.py`.

## Authoritative Data Sources
CFPB (consumerfinance.gov), NBER (nber.org), SSRN household finance
(ssrn.com), OECD/World Bank financial-literacy (oecd.org), central-bank
policy-rate pages.

## Analytical Frameworks (canonical implementations)
All formulas below are implemented deterministically in
`tools/planner_engine.py` so the skill produces auditable, reproducible output.

- `emergency_fund_months = liquid_savings / (needs + min_debt_payments)`
- `dti = sum(min_debt_payments) / gross_income`
- `savings_rate = (savings_expense + max(0, surplus)) / take_home`
- `budget_deviation = (|needs%-50%| + |wants%-30%| + |savings%-20%|) / 2`
- `concentration = max(holding_value) / investable_assets`
- avalanche payoff: highest-APR-first amortization
- snowball payoff: smallest-balance-first amortization
- goal feasibility: `monthly_contribution >= target / (horizon_years*12)`

## Self-Update Protocol
- Sources: CFPB, NBER, SSRN, OECD. Frequency: weekly (cron).
- Dedupe by 12-char SHA1 hash of `url|title`, embedded as `<!--h:hash-->`.
- Append format:
  `- [DATE] Title - Source - URL <!--h:hash-->`
- Config: `tools/knowledge_sources.json`. Runner: `tools/knowledge_updater.py`.

## Knowledge Update Log
- [2026-06-18] Seed entry - core frameworks & benchmarks documented.
- [2026-07-01] Engine + regions + harness wired; formulas canonized; sources expanded.
