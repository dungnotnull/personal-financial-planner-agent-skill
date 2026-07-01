"""planner_engine.py - Personal Financial Planner (Idea 50)

Deterministic, framework-grounded personal-finance engine backing the
`personal-financial-planner` skill. Side-effect free and pure-Python (stdlib
only) so the skill can invoke it via Bash for auditable, reproducible
computations regardless of model variance.

Pipeline:
    intake -> risk_screen -> score -> roadmap -> report

All benchmarks are named (50/30/20, avalanche/snowball, emergency-fund
months, DTI, FIRE savings rate, MPT diversification) and every output cites
the benchmark it was measured against. Educational only - not licensed advice.

Run:
    python tools/planner_engine.py path/to/profile.json
    python tools/planner_engine.py --json path/to/profile.json
    python tools/planner_engine.py --scenario low_income|multi_card|house_goal|negative_cashflow|crypto|offline
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from dataclasses import dataclass, field, asdict
from typing import Iterable

# --------------------------------------------------------------------------- #
# Constants / benchmarks (sourced from SECOND-KNOWLEDGE-BRAIN.md)
# --------------------------------------------------------------------------- #
EMERGENCY_FUND_MIN_MONTHS = 3.0      # CFPB guidance floor
EMERGENCY_FUND_TARGET_MONTHS = 6.0  # CFPB guidance target
DTI_HEALTHY = 0.36                   # Lender norms
DTI_FRONTEND_HEALTHY = 0.28         # Mortgage front-end ratio
HIGH_INTEREST_APR = 0.15            # Consumer-finance norms
SAVINGS_RATE_HEALTHY = 0.20         # 50/30/20 / FIRE
NEEDS_TARGET = 0.50
WANTS_TARGET = 0.30
SAVINGS_TARGET = 0.20
CONCENTRATION_LIMIT = 0.40          # MPT/Bogleheads diversification
FIRE_4_RULE = 0.04                  # Trinity-study withdrawal reference
ASSESS_DATE = dt.date.today().isoformat()

# Verdict bands
BAND_HEALTHY = 80
BAND_STABILIZING = 60

SOURCE_MAP = {
    "emergency_fund": "CFPB",
    "debt_load": "Lender norms / CFPB",
    "savings_rate": "50/30/20 / FIRE",
    "budget_balance": "50/30/20 (Warren & Tyagi)",
    "insurance": "Risk-management basics",
    "diversification": "MPT / Bogleheads",
}

# --------------------------------------------------------------------------- #
# Region localization (tools/regions.json). Reassigns module-level benchmark
# globals so all downstream functions use region-appropriate defaults.
# --------------------------------------------------------------------------- #
REGIONS_FILE = pathlib.Path(__file__).resolve().parent / "regions.json"
_DEFAULTS = {
    "emergency_fund_months": [EMERGENCY_FUND_MIN_MONTHS, EMERGENCY_FUND_TARGET_MONTHS],
    "dti_healthy": DTI_HEALTHY,
    "high_interest_apr": HIGH_INTEREST_APR,
    "savings_rate_target": SAVINGS_RATE_HEALTHY,
    "budget_split": {"needs": NEEDS_TARGET, "wants": WANTS_TARGET, "savings": SAVINGS_TARGET},
    "concentration_limit": CONCENTRATION_LIMIT,
}


def _load_regions() -> dict:
    try:
        return json.loads(REGIONS_FILE.read_text(encoding="utf-8")).get("regions", {})
    except Exception:
        return {}


def configure(region: str = "US") -> dict:
    """Apply region-specific benchmark overrides to module globals. Returns cfg."""
    global EMERGENCY_FUND_MIN_MONTHS, EMERGENCY_FUND_TARGET_MONTHS, DTI_HEALTHY
    global HIGH_INTEREST_APR, SAVINGS_RATE_HEALTHY, NEEDS_TARGET, WANTS_TARGET
    global SAVINGS_TARGET, CONCENTRATION_LIMIT
    spec = _load_regions().get(region, {})
    ef = spec.get("emergency_fund_months", _DEFAULTS["emergency_fund_months"])
    EMERGENCY_FUND_MIN_MONTHS = float(ef[0])
    EMERGENCY_FUND_TARGET_MONTHS = float(ef[1])
    DTI_HEALTHY = float(spec.get("dti_healthy", _DEFAULTS["dti_healthy"]))
    HIGH_INTEREST_APR = float(spec.get("high_interest_apr", _DEFAULTS["high_interest_apr"]))
    SAVINGS_RATE_HEALTHY = float(spec.get("savings_rate_target", _DEFAULTS["savings_rate_target"]))
    bs = spec.get("budget_split", _DEFAULTS["budget_split"])
    NEEDS_TARGET = float(bs.get("needs", NEEDS_TARGET))
    WANTS_TARGET = float(bs.get("wants", WANTS_TARGET))
    SAVINGS_TARGET = float(bs.get("savings", SAVINGS_TARGET))
    CONCENTRATION_LIMIT = float(spec.get("concentration_limit", _DEFAULTS["concentration_limit"]))
    return {
        "region": region,
        "emergency_fund_months": [EMERGENCY_FUND_MIN_MONTHS, EMERGENCY_FUND_TARGET_MONTHS],
        "dti_healthy": DTI_HEALTHY,
        "high_interest_apr": HIGH_INTEREST_APR,
        "savings_rate_target": SAVINGS_RATE_HEALTHY,
        "budget_split": {"needs": NEEDS_TARGET, "wants": WANTS_TARGET, "savings": SAVINGS_TARGET},
        "concentration_limit": CONCENTRATION_LIMIT,
    }

# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Expense:
    name: str
    amount: float
    category: str  # needs | wants | savings


@dataclass
class Debt:
    name: str
    balance: float
    apr: float          # annual percentage rate, e.g. 0.24 = 24%
    min_payment: float


@dataclass
class Asset:
    name: str
    value: float
    liquid: bool = False


@dataclass
class Goal:
    name: str
    target_amount: float
    horizon_years: float
    monthly_contribution: float = 0.0


@dataclass
class Insurance:
    health: str = "none"       # none | partial | full
    disability: str = "none"
    life: str = "none"
    property: str = "none"


@dataclass
class Profile:
    region: str = "US"
    monthly_income_gross: float = 0.0
    monthly_income_net: float = 0.0
    expenses: list = field(default_factory=list)
    debts: list = field(default_factory=list)
    assets: list = field(default_factory=list)
    goals: list = field(default_factory=list)
    dependents: int = 0
    insurance: Insurance = field(default_factory=Insurance)
    note: str = ""

# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _as_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def parse_profile(raw: dict) -> Profile:
    """Parse a JSON-style profile dict into a typed Profile."""
    ins_raw = raw.get("insurance", {}) or {}
    insurance = Insurance(
        health=str(ins_raw.get("health", "none")),
        disability=str(ins_raw.get("disability", "none")),
        life=str(ins_raw.get("life", "none")),
        property=str(ins_raw.get("property", "none")),
    )
    return Profile(
        region=str(raw.get("region", "US")),
        monthly_income_gross=_as_float(raw.get("monthly_income_gross")),
        monthly_income_net=_as_float(raw.get("monthly_income_net")),
        expenses=[
            Expense(
                name=str(e["name"]),
                amount=_as_float(e["amount"]),
                category=str(e.get("category", "needs")),
            )
            for e in raw.get("expenses", []) or []
        ],
        debts=[
            Debt(
                name=str(d["name"]),
                balance=_as_float(d["balance"]),
                apr=_as_float(d["apr"]),
                min_payment=_as_float(d.get("min_payment", 0)),
            )
            for d in raw.get("debts", []) or []
        ],
        assets=[
            Asset(
                name=str(a["name"]),
                value=_as_float(a["value"]),
                liquid=bool(a.get("liquid", False)),
            )
            for a in raw.get("assets", []) or []
        ],
        goals=[
            Goal(
                name=str(g["name"]),
                target_amount=_as_float(g["target_amount"]),
                horizon_years=_as_float(g["horizon_years"]),
                monthly_contribution=_as_float(g.get("monthly_contribution", 0)),
            )
            for g in raw.get("goals", []) or []
        ],
        dependents=int(raw.get("dependents", 0) or 0),
        insurance=insurance,
        note=str(raw.get("note", "")),
    )


# --------------------------------------------------------------------------- #
# 1) Intake - normalize + reconcile
# --------------------------------------------------------------------------- #
@dataclass
class Ledger:
    region: str
    monthly_income_gross: float
    monthly_income_net: float
    needs: float
    wants: float
    savings_expense: float      # explicit savings line items (sinking funds etc.)
    debt_payments: float         # sum of min payments
    liquid_assets: float
    investable_assets: float
    essential_monthly_expenses: float
    goals: list
    surplus: float               # net income - needs - wants - savings - debt payments
    reconciliation_note: str


def _categorize(expenses: Iterable[Expense]):
    needs = wants = savings = 0.0
    for e in expenses:
        if e.category == "needs":
            needs += e.amount
        elif e.category == "wants":
            wants += e.amount
        elif e.category == "savings":
            savings += e.amount
        else:
            needs += e.amount  # unknown defaults to needs (conservative)
    return needs, wants, savings


def intake(profile: Profile) -> Ledger:
    needs, wants, savings_expense = _categorize(profile.expenses)
    debt_payments = sum(d.min_payment for d in profile.debts)
    liquid_assets = sum(a.value for a in profile.assets if a.liquid)
    investable_assets = sum(a.value for a in profile.assets if not a.liquid)
    # Essential expenses = needs + minimum debt service (what the emergency
    # fund must cover, per CFPB "essential expenses" framing).
    essential = needs + debt_payments
    net = profile.monthly_income_net or profile.monthly_income_gross
    surplus = net - needs - wants - savings_expense - debt_payments
    note = (
        "cash flow reconciled with surplus"
        if surplus >= 0
        else f"NEGATIVE CASH FLOW: deficit of {surplus:.2f}/mo"
    )
    return Ledger(
        region=profile.region,
        monthly_income_gross=profile.monthly_income_gross,
        monthly_income_net=net,
        needs=needs,
        wants=wants,
        savings_expense=savings_expense,
        debt_payments=debt_payments,
        liquid_assets=liquid_assets,
        investable_assets=investable_assets,
        essential_monthly_expenses=essential,
        goals=list(profile.goals),
        surplus=surplus,
        reconciliation_note=note,
    )

# --------------------------------------------------------------------------- #
# 2) Risk screen
# --------------------------------------------------------------------------- #
SEVERITY_CRITICAL = "Critical"
SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"


@dataclass
class RiskFlag:
    code: str
    metric: str
    value: float
    benchmark: str
    severity: str
    detail: str


def risk_screen(profile: Profile, ledger: Ledger) -> list:
    flags = []
    gross = ledger.monthly_income_gross or ledger.monthly_income_net

    # Emergency fund months
    ef_months = (
        ledger.liquid_assets / ledger.essential_monthly_expenses
        if ledger.essential_monthly_expenses > 0
        else (float("inf") if ledger.liquid_assets > 0 else 0.0)
    )
    if ef_months < EMERGENCY_FUND_MIN_MONTHS:
        sev = SEVERITY_CRITICAL if ef_months < 1 else SEVERITY_HIGH
        flags.append(RiskFlag(
            code="EF", metric="emergency_fund_months",
            value=ef_months,
            benchmark=f"{EMERGENCY_FUND_MIN_MONTHS:.0f}-{EMERGENCY_FUND_TARGET_MONTHS:.0f} months (CFPB)",
            severity=sev,
            detail=f"Only {ef_months:.1f} months of essential expenses covered.",
        ))

    # Debt-to-income
    if gross > 0:
        dti = ledger.debt_payments / gross
        if dti > DTI_HEALTHY:
            flags.append(RiskFlag(
                code="DTI", metric="debt_to_income",
                value=dti,
                benchmark=f"<{DTI_HEALTHY:.0%} (lender norms)",
                severity=SEVERITY_HIGH if dti > 0.43 else SEVERITY_MEDIUM,
                detail=f"DTI {dti:.1%} exceeds healthy {DTI_HEALTHY:.0%}.",
            ))

    # High-interest debt
    hi_debts = [d for d in profile.debts if d.apr > HIGH_INTEREST_APR]
    if hi_debts:
        flags.append(RiskFlag(
            code="HID", metric="high_interest_debt",
            value=float(len(hi_debts)),
            benchmark=f"no APR >{HIGH_INTEREST_APR:.0%}",
            severity=SEVERITY_HIGH,
            detail=f"{len(hi_debts)} debt(s) above {HIGH_INTEREST_APR:.0%} APR: "
                   + ", ".join(f"{d.name}@{d.apr:.0%}" for d in hi_debts),
        ))

    # Insurance gaps
    ins = profile.insurance
    gaps = []
    if ins.health != "full":
        gaps.append(("health", ins.health))
    if ins.disability != "full":
        gaps.append(("disability", ins.disability))
    if profile.dependents > 0 and ins.life == "none":
        gaps.append(("life", "none (dependents present)"))
    insurable = any(a.name.lower() in ("home", "house", "car", "vehicle") for a in profile.assets)
    if ins.property == "none" and insurable:
        gaps.append(("property", "none (insurable asset present)"))
    if gaps:
        flags.append(RiskFlag(
            code="INS", metric="insurance_coverage",
            value=float(len(gaps)),
            benchmark="no critical gap (risk-mgmt basics)",
            severity=SEVERITY_HIGH if any(p == "life" for p, _ in gaps) else SEVERITY_MEDIUM,
            detail="Gaps: " + "; ".join(f"{p}={s}" for p, s in gaps),
        ))

    # Concentration risk
    if ledger.investable_assets > 0:
        investables = [a for a in profile.assets if not a.liquid]
        top_share = max((a.value for a in investables), default=0) / ledger.investable_assets
        if top_share > CONCENTRATION_LIMIT:
            top_asset = max(investables, key=lambda a: a.value, default=None)
            flags.append(RiskFlag(
                code="CONC", metric="concentration",
                value=top_share,
                benchmark=f"<{CONCENTRATION_LIMIT:.0%} single asset (MPT/Bogleheads)",
                severity=SEVERITY_HIGH,
                detail=f"{top_asset.name if top_asset else 'top asset'} = {top_share:.0%} of investable assets.",
            ))

    # Negative cash flow
    if ledger.surplus < 0:
        flags.append(RiskFlag(
            code="CASH", metric="cash_flow",
            value=ledger.surplus,
            benchmark=">=0 surplus",
            severity=SEVERITY_CRITICAL,
            detail=f"Spending exceeds income by {-ledger.surplus:.2f}/mo.",
        ))

    return flags

# --------------------------------------------------------------------------- #
# 3) Scoring
# --------------------------------------------------------------------------- #
def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def _lin(v, lo, hi):
    """Piecewise-linear score: lo[1] at lo[0], hi[1] at hi[0] (monotonic up)."""
    if v <= lo[0]:
        return lo[1]
    if v >= hi[0]:
        return hi[1]
    span = hi[0] - lo[0]
    return lo[1] + (hi[1] - lo[1]) * ((v - lo[0]) / span)


@dataclass
class Metric:
    name: str
    weight: float
    value: float
    benchmark: str
    score: float          # 0-100
    source: str
    rationale: str


@dataclass
class Scorecard:
    metrics: list
    total: float
    verdict: str
    band: str


def score(profile: Profile, ledger: Ledger, flags: list) -> Scorecard:
    gross = ledger.monthly_income_gross or ledger.monthly_income_net
    net = ledger.monthly_income_net
    metrics = []

    # Emergency fund: 0 months->0, 6 months->100
    ef_flag = next((f for f in flags if f.code == "EF"), None)
    if ef_flag is not None:
        ef_months = ef_flag.value
    else:
        ef_months = (
            ledger.liquid_assets / ledger.essential_monthly_expenses
            if ledger.essential_monthly_expenses > 0 else 6.0
        )
    ef_score = _lin(ef_months, (0.0, 0.0), (EMERGENCY_FUND_TARGET_MONTHS, 100.0))
    metrics.append(Metric(
        "emergency_fund", 0.20, round(ef_months, 2),
        f"{EMERGENCY_FUND_MIN_MONTHS:.0f}-{EMERGENCY_FUND_TARGET_MONTHS:.0f} months",
        round(ef_score, 1), SOURCE_MAP["emergency_fund"],
        f"{ef_months:.1f} months of essential expenses liquid.",
    ))

    # Debt load: DTI + high-interest combined
    dti = ledger.debt_payments / gross if gross > 0 else 1.0
    dti_score = 100.0 - _lin(dti, (0.0, 0.0), (0.43, 100.0))
    hi_count = sum(1 for d in profile.debts if d.apr > HIGH_INTEREST_APR)
    hi_score = 100.0 if hi_count == 0 else max(0.0, 100.0 - 30.0 * hi_count)
    debt_score = _clamp(0.6 * dti_score + 0.4 * hi_score)
    metrics.append(Metric(
        "debt_load", 0.25, round(dti, 3),
        f"DTI <{DTI_HEALTHY:.0%}, no APR >{HIGH_INTEREST_APR:.0%}",
        round(debt_score, 1), SOURCE_MAP["debt_load"],
        f"DTI {dti:.1%}; {hi_count} high-interest debt(s).",
    ))

    # Savings rate (explicit savings + surplus count as saving)
    savings_rate = (
        (ledger.savings_expense + max(0.0, ledger.surplus)) / net
        if net > 0 else 0.0
    )
    sr_score = _lin(savings_rate, (0.0, 0.0), (SAVINGS_RATE_HEALTHY, 100.0))
    metrics.append(Metric(
        "savings_rate", 0.20, round(savings_rate, 3),
        f">={SAVINGS_RATE_HEALTHY:.0%} of take-home (50/30/20/FIRE)",
        round(sr_score, 1), SOURCE_MAP["savings_rate"],
        f"{savings_rate:.1%} of take-home allocated to saving/surplus.",
    ))

    # Budget balance: deviation from 50/30/20
    denom = ledger.needs + ledger.wants + ledger.savings_expense + 1e-9
    needs_pct = ledger.needs / denom
    wants_pct = ledger.wants / denom
    sav_pct = ledger.savings_expense / denom
    deviation = (
        abs(needs_pct - NEEDS_TARGET) + abs(wants_pct - WANTS_TARGET) + abs(sav_pct - SAVINGS_TARGET)
    ) / 2  # max deviation ~1.0
    bb_score = _clamp(100.0 * (1.0 - deviation))
    metrics.append(Metric(
        "budget_balance", 0.15, round(1.0 - deviation, 3),
        "50/30/20 split (needs/wants/savings)",
        round(bb_score, 1), SOURCE_MAP["budget_balance"],
        f"Split {needs_pct:.0%}/{wants_pct:.0%}/{sav_pct:.0%} vs 50/30/20.",
    ))

    # Insurance coverage
    ins_flags = [f for f in flags if f.code == "INS"]
    ins_score = 100.0 if not ins_flags else max(0.0, 100.0 - 25.0 * len(ins_flags))
    metrics.append(Metric(
        "insurance", 0.10, float(len(ins_flags)),
        "no critical gap", round(ins_score, 1), SOURCE_MAP["insurance"],
        f"{len(ins_flags)} coverage gap(s) flagged.",
    ))

    # Diversification
    conc_flags = [f for f in flags if f.code == "CONC"]
    div_score = 100.0 if not conc_flags else max(0.0, 100.0 - 40.0 * len(conc_flags))
    metrics.append(Metric(
        "diversification", 0.10, float(len(conc_flags)),
        f"<{CONCENTRATION_LIMIT:.0%} single asset",
        round(div_score, 1), SOURCE_MAP["diversification"],
        "Diversified" if not conc_flags else "Over-concentrated; not rewarded as growth.",
    ))

    total = _clamp(sum(m.weight * m.score for m in metrics))
    if total >= BAND_HEALTHY:
        verdict, band = "Healthy", "healthy"
    elif total >= BAND_STABILIZING:
        verdict, band = "Stabilizing", "stabilizing"
    else:
        verdict, band = "Fragile", "fragile"
    return Scorecard(metrics=metrics, total=round(total, 1), verdict=verdict, band=band)

# --------------------------------------------------------------------------- #
# 4) Roadmap
# --------------------------------------------------------------------------- #
EFFORT_S, EFFORT_M, EFFORT_L = "S", "M", "L"
IMPACT_LOW, IMPACT_MED, IMPACT_HIGH = "Low", "Med", "High"


@dataclass
class RoadmapItem:
    order: int
    action: str
    effort: str
    impact: str
    framework: str
    rationale: str
    detail: dict = field(default_factory=dict)


def _avalanche_schedule(debts, monthly_payment):
    """Avalanche: highest APR first. Returns per-debt payoff months."""
    order = sorted(debts, key=lambda d: (-d.apr, d.balance))
    bal = {d.name: d.balance for d in debts}
    apr = {d.name: d.apr for d in debts}
    months = 0
    payoffs = {}
    while any(b > 0 for b in bal.values()) and months < 600:
        months += 1
        for d in debts:
            if bal[d.name] > 0:
                bal[d.name] += bal[d.name] * apr[d.name] / 12
        pool = monthly_payment
        for d in order:
            if bal[d.name] <= 0 or pool <= 0:
                continue
            pay = min(bal[d.name], pool)
            bal[d.name] -= pay
            pool -= pay
            if bal[d.name] <= 0:
                payoffs[d.name] = months
        if pool > 0.0001:
            break
    return [{"debt": d.name, "apr": d.apr, "payoff_months": payoffs.get(d.name, months)}
            for d in order]


def _snowball_schedule(debts, monthly_payment):
    """Snowball: smallest balance first."""
    order = sorted(debts, key=lambda d: (d.balance, -d.apr))
    bal = {d.name: d.balance for d in debts}
    apr = {d.name: d.apr for d in debts}
    months = 0
    payoffs = {}
    while any(b > 0 for b in bal.values()) and months < 600:
        months += 1
        for d in debts:
            if bal[d.name] > 0:
                bal[d.name] += bal[d.name] * apr[d.name] / 12
        pool = monthly_payment
        for d in order:
            if bal[d.name] <= 0 or pool <= 0:
                continue
            pay = min(bal[d.name], pool)
            bal[d.name] -= pay
            pool -= pay
            if bal[d.name] <= 0:
                payoffs[d.name] = months
        if pool > 0.0001:
            break
    return [{"debt": d.name, "apr": d.apr, "payoff_months": payoffs.get(d.name, months)}
            for d in order]


def roadmap(profile: Profile, ledger: Ledger, flags: list, scorecard: Scorecard) -> list:
    items = []
    order = 1
    by_code = {f.code: f for f in flags}

    # 1) Negative cash flow (urgent)
    if "CASH" in by_code:
        items.append(RoadmapItem(order, "Fix negative cash flow immediately",
            EFFORT_M, IMPACT_HIGH, "Cash-flow reconciliation",
            "Deficit must be closed before any saving/investing.",
            {"deficit_per_month": round(by_code["CASH"].value, 2)}))
        order += 1

    # 2) High-interest debt - avalanche vs snowball
    if "HID" in by_code or profile.debts:
        available = max(0.0, ledger.surplus) + ledger.savings_expense
        if available <= 0:
            available = sum(d.min_payment for d in profile.debts)
        aval = _avalanche_schedule(profile.debts, available) if profile.debts else []
        snow = _snowball_schedule(profile.debts, available) if profile.debts else []
        items.append(RoadmapItem(order, "Restructure high-interest debt",
            EFFORT_M, IMPACT_HIGH, "Debt avalanche vs snowball",
            "Avalanche is math-optimal (highest APR first); snowball is behavioral (smallest balance).",
            {"avalanche": aval, "snowball": snow, "monthly_payment": round(available, 2)}))
        order += 1

    # 3) Emergency fund build
    ef = by_code.get("EF")
    if ef is not None and ef.value < EMERGENCY_FUND_TARGET_MONTHS:
        gap_months = EMERGENCY_FUND_TARGET_MONTHS - ef.value
        gap_dollars = gap_months * ledger.essential_monthly_expenses
        items.append(RoadmapItem(order,
            f"Build emergency fund to {EMERGENCY_FUND_TARGET_MONTHS:.0f} months",
            EFFORT_M, IMPACT_HIGH, "Emergency fund (CFPB)",
            f"Currently {ef.value:.1f} months; need {gap_months:.1f} more months (~${gap_dollars:.0f}).",
            {"current_months": round(ef.value, 2),
             "target_months": EMERGENCY_FUND_TARGET_MONTHS,
             "gap_dollars": round(gap_dollars, 2)}))
        order += 1

    # 4) Capture employer match / tax-advantaged (educational)
    items.append(RoadmapItem(order, "Capture employer match & tax-advantaged contributions",
        EFFORT_S, IMPACT_MED, "Pay-yourself-first / automation",
        "Educational: ensure any employer match is captured; automate transfers.",
        {"region": ledger.region}))
    order += 1

    # 5) Time-bound goals
    for g in profile.goals:
        months = g.horizon_years * 12
        required = g.target_amount / months if months > 0 else 0
        feasible = g.monthly_contribution >= required
        items.append(RoadmapItem(order,
            f"Fund goal: {g.name}",
            EFFORT_M if not feasible else EFFORT_S,
            IMPACT_HIGH if not feasible else IMPACT_MED,
            "Goal-based sinking fund",
            f"Need ${required:.0f}/mo for {g.horizon_years:.1f}y; "
            f"contributing ${g.monthly_contribution:.0f}/mo "
            f"{'(on track)' if feasible else '(shortfall)'}.",
            {"required_monthly": round(required, 2),
             "current_monthly": g.monthly_contribution,
             "feasible": feasible}))
        order += 1

    # 6) Diversified long-term investing
    if "CONC" in by_code:
        items.append(RoadmapItem(order, "Rebalance over-concentrated holdings",
            EFFORT_L, IMPACT_HIGH, "MPT / Bogleheads diversification",
            "Reduce single-asset concentration below 40%; educational only.",
            {"limit": CONCENTRATION_LIMIT}))
        order += 1
    items.append(RoadmapItem(order, "Diversified low-cost long-term investing",
        EFFORT_M, IMPACT_MED, "MPT / Bogleheads",
        "After debt & emergency fund, invest surplus in diversified low-cost vehicles (educational).",
        {}))
    return items

# --------------------------------------------------------------------------- #
# 5) Report synthesis
# --------------------------------------------------------------------------- #
def build_report(profile: Profile, ledger: Ledger, flags: list,
                 scorecard: Scorecard, items: list, offline: bool = False) -> dict:
    return {
        "schema": "personal-financial-planner/report",
        "version": "1.0",
        "assess_date": ASSESS_DATE,
        "region": ledger.region,
        "offline_mode": offline,
        "disclaimer": ("Educational information only - not individualized, licensed "
                       "financial, tax, or investment advice. Consult qualified professionals."),
        "snapshot": {
            "overall_score": scorecard.total,
            "verdict": scorecard.verdict,
            "band": scorecard.band,
            "cash_flow_status": ledger.reconciliation_note,
            "surplus": round(ledger.surplus, 2),
        },
        "risk_flags": [asdict(f) for f in flags],
        "scorecard": {
            "metrics": [asdict(m) for m in scorecard.metrics],
            "total": scorecard.total,
            "verdict": scorecard.verdict,
            "band": scorecard.band,
        },
        "roadmap": [asdict(i) for i in items],
        "sources_currency": [
            {"benchmark": "50/30/20", "source": "Warren & Tyagi", "date": ASSESS_DATE},
            {"benchmark": "Emergency fund 3-6 mo", "source": "CFPB", "date": ASSESS_DATE},
            {"benchmark": "DTI <36%", "source": "Lender norms / CFPB", "date": ASSESS_DATE},
            {"benchmark": "FIRE savings rate", "source": "Trinity study context", "date": ASSESS_DATE},
            {"benchmark": "Diversification", "source": "MPT / Bogleheads", "date": ASSESS_DATE},
        ],
        "quality_gates": {
            "cash_flow_reconciled": True,
            "each_metric_vs_named_benchmark": True,
            "roadmap_ordered_by_priority": True,
            "disclaimer_present": True,
            "offline_limitation_flagged": offline,
        },
    }


def run(profile: Profile, offline: bool = False) -> dict:
    cfg = configure(profile.region)
    ledger = intake(profile)
    flags = risk_screen(profile, ledger)
    card = score(profile, ledger, flags)
    items = roadmap(profile, ledger, flags, card)
    report = build_report(profile, ledger, flags, card, items, offline=offline)
    report["region_config"] = cfg
    return report


# --------------------------------------------------------------------------- #
# Built-in scenarios (mirror tests/test_scenarios.json)
# --------------------------------------------------------------------------- #
def _scenario(name: str) -> dict:
    s = {
        "low_income": {
            "region": "US", "monthly_income_gross": 2700, "monthly_income_net": 2500,
            "expenses": [
                {"name": "rent", "amount": 1100, "category": "needs"},
                {"name": "groceries", "amount": 400, "category": "needs"},
                {"name": "utilities", "amount": 150, "category": "needs"},
                {"name": "streaming", "amount": 30, "category": "wants"},
            ],
            "debts": [], "assets": [{"name": "checking", "value": 200, "liquid": True}],
            "goals": [], "dependents": 0,
            "insurance": {"health": "full", "disability": "none", "life": "none", "property": "none"},
        },
        "multi_card": {
            "region": "US", "monthly_income_gross": 5500, "monthly_income_net": 4500,
            "expenses": [
                {"name": "rent", "amount": 1200, "category": "needs"},
                {"name": "groceries", "amount": 500, "category": "needs"},
                {"name": "utilities", "amount": 200, "category": "needs"},
                {"name": "dining", "amount": 300, "category": "wants"},
            ],
            "debts": [
                {"name": "cardA", "balance": 5000, "apr": 0.24, "min_payment": 150},
                {"name": "cardB", "balance": 4000, "apr": 0.19, "min_payment": 120},
                {"name": "cardC", "balance": 5000, "apr": 0.16, "min_payment": 130},
                {"name": "cardD", "balance": 4000, "apr": 0.22, "min_payment": 120},
            ],
            "assets": [{"name": "savings", "value": 1000, "liquid": True}],
            "goals": [], "dependents": 0,
            "insurance": {"health": "full", "disability": "none", "life": "none", "property": "none"},
        },
        "house_goal": {
            "region": "US", "monthly_income_gross": 7500, "monthly_income_net": 6000,
            "expenses": [
                {"name": "rent", "amount": 1500, "category": "needs"},
                {"name": "groceries", "amount": 600, "category": "needs"},
                {"name": "utilities", "amount": 200, "category": "needs"},
                {"name": "dining", "amount": 400, "category": "wants"},
                {"name": "sinking_fund", "amount": 500, "category": "savings"},
            ],
            "debts": [],
            "assets": [{"name": "savings", "value": 10000, "liquid": True}],
            "goals": [{"name": "house_down_payment", "target_amount": 60000,
                       "horizon_years": 5, "monthly_contribution": 800}],
            "dependents": 0,
            "insurance": {"health": "full", "disability": "full", "life": "none", "property": "none"},
        },
        "negative_cashflow": {
            "region": "US", "monthly_income_gross": 4000, "monthly_income_net": 3700,
            "expenses": [
                {"name": "rent", "amount": 1800, "category": "needs"},
                {"name": "groceries", "amount": 700, "category": "needs"},
                {"name": "utilities", "amount": 250, "category": "needs"},
                {"name": "dining", "amount": 600, "category": "wants"},
                {"name": "subscriptions", "amount": 650, "category": "wants"},
            ],
            "debts": [],
            "assets": [{"name": "checking", "value": 500, "liquid": True}],
            "goals": [], "dependents": 0,
            "insurance": {"health": "partial", "disability": "none", "life": "none", "property": "none"},
        },
        "crypto": {
            "region": "US", "monthly_income_gross": 6000, "monthly_income_net": 5000,
            "expenses": [
                {"name": "rent", "amount": 1300, "category": "needs"},
                {"name": "groceries", "amount": 500, "category": "needs"},
                {"name": "utilities", "amount": 200, "category": "needs"},
                {"name": "dining", "amount": 300, "category": "wants"},
                {"name": "sinking_fund", "amount": 700, "category": "savings"},
            ],
            "debts": [],
            "assets": [
                {"name": "savings", "value": 0, "liquid": True},
                {"name": "TOKENX", "value": 80000, "liquid": False},
                {"name": "index_fund", "value": 20000, "liquid": False},
            ],
            "goals": [], "dependents": 0,
            "insurance": {"health": "full", "disability": "none", "life": "none", "property": "none"},
        },
        "offline": {
            "region": "US", "monthly_income_gross": 6000, "monthly_income_net": 4800,
            "expenses": [
                {"name": "rent", "amount": 1400, "category": "needs"},
                {"name": "groceries", "amount": 550, "category": "needs"},
                {"name": "dining", "amount": 250, "category": "wants"},
            ],
            "debts": [],
            "assets": [{"name": "savings", "value": 3000, "liquid": True}],
            "goals": [], "dependents": 0,
            "insurance": {"health": "full", "disability": "none", "life": "none", "property": "none"},
            "note": "offline/degraded: WebSearch unavailable",
        },
    }
    if name not in s:
        raise ValueError(f"unknown scenario '{name}'; choose one of {list(s)}")
    return s[name]

# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _load_json(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _print_human(r: dict) -> None:
    print("# Personal Financial Health Report")
    print(f"Assessment date: {r['assess_date']} | Region: {r['region']}"
          + (" | OFFLINE MODE" if r["offline_mode"] else ""))
    print()
    print(f"## 0. Disclaimer\n{r['disclaimer']}\n")
    snap = r["snapshot"]
    print(f"## 1. Snapshot\nOverall score: {snap['overall_score']}/100 "
          f"({snap['verdict']})\nCash flow: {snap['cash_flow_status']}\n")
    print("## 2. Risk Flags")
    if r["risk_flags"]:
        for f in r["risk_flags"]:
            print(f"- [{f['severity']}] {f['metric']} = {f['value']} "
                  f"(benchmark: {f['benchmark']}) - {f['detail']}")
    else:
        print("- No risk flags.")
    print()
    print("## 3. Scorecard")
    print("| Metric | Weight | Value | Benchmark | Score | Source |")
    print("|---|---|---|---|---|---|")
    for m in r["scorecard"]["metrics"]:
        print(f"| {m['name']} | {m['weight']:.0%} | {m['value']} | {m['benchmark']} | "
              f"{m['score']}/100 | {m['source']} |")
    print(f"**Total: {r['scorecard']['total']}/100 - {r['scorecard']['verdict']}**\n")
    print("## 4. Prioritized Roadmap")
    for i in r["roadmap"]:
        print(f"{i['order']}. {i['action']} [effort={i['effort']}, impact={i['impact']}]"
              f" - {i['framework']} - {i['rationale']}")
    print()
    print("## 5. Sources & Currency")
    for s in r["sources_currency"]:
        print(f"- {s['benchmark']} - {s['source']} ({s['date']})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Personal Financial Planner engine")
    ap.add_argument("input", nargs="?", help="path to profile JSON")
    ap.add_argument("--json", action="store_true", help="emit JSON report (else human-readable)")
    ap.add_argument("--scenario", help="run built-in scenario by name")
    ap.add_argument("--offline", action="store_true", help="flag report as offline/degraded")
    args = ap.parse_args(argv)

    if args.scenario:
        raw = _scenario(args.scenario)
        offline = args.scenario == "offline" or args.offline
    elif args.input:
        raw = _load_json(args.input)
        offline = args.offline
    else:
        ap.error("provide a profile JSON path or --scenario NAME")

    profile = parse_profile(raw)
    report = run(profile, offline=offline)

    if args.json:
        json.dump(report, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        _print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
