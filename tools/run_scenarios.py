"""run_scenarios.py - Personal Financial Planner (Idea 50)

Deterministic scenario harness that runs every fixture through
planner_engine.run() and asserts each scenario's quality gates pass.
Exit code 0 = all pass, non-zero = failures. No network, no models.

Run:
    python tools/run_scenarios.py
    python tools/run_scenarios.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import planner_engine as eng  # noqa: E402

FIXTURES = pathlib.Path(HERE.parent / "tests" / "test_scenarios.json")


def _load_fixtures() -> dict:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def _flags_by_code(report: dict) -> set:
    return {f["code"] for f in report["risk_flags"]}


def _roadmap_actions(report: dict) -> list:
    return [i["action"] for i in report["roadmap"]]


# Per-scenario assertion functions. Each returns list of error strings.
def check_low_income(r):
    errs = []
    if not r["disclaimer"]:
        errs.append("disclaimer missing")
    if "EF" not in _flags_by_code(r):
        errs.append("emergency-fund flag expected")
    actions = _roadmap_actions(r)
    if not any("emergency fund" in a.lower() for a in actions):
        errs.append("roadmap must include emergency-fund build")
    if not any("benchmark" in m["benchmark"] or "months" in m["benchmark"]
               for m in r["scorecard"]["metrics"]):
        errs.append("scorecard must cite benchmarks")
    return errs


def check_multi_card(r):
    errs = []
    flags = _flags_by_code(r)
    if "HID" not in flags:
        errs.append("high-interest-debt flag expected")
    debt_item = next((i for i in r["roadmap"] if "debt" in i["action"].lower()), None)
    if not debt_item:
        errs.append("debt restructure roadmap item missing")
    else:
        d = debt_item["detail"]
        if "avalanche" not in d or "snowball" not in d:
            errs.append("both avalanche and snowball schedules required")
        if not d["avalanche"] or not d["snowball"]:
            errs.append("payoff schedules must be populated")
    # High-interest debt must precede diversified-investing
    actions = _roadmap_actions(r)
    if any("debt" in a.lower() for a in actions):
        inv_idx = next((i for i, a in enumerate(actions) if "investing" in a.lower()), None)
        debt_idx = next((i for i, a in enumerate(actions) if "debt" in a.lower()), None)
        if inv_idx is not None and debt_idx is not None and debt_idx > inv_idx:
            errs.append("debt must precede investing in roadmap")
    return errs


def check_house_goal(r):
    errs = []
    goal_item = next((i for i in r["roadmap"] if "house_down_payment" in i["action"]), None)
    if not goal_item:
        errs.append("house goal roadmap item missing")
    else:
        req = goal_item["detail"]["required_monthly"]
        if req <= 0:
            errs.append("required monthly savings must be computed")
        if not isinstance(goal_item["detail"]["feasible"], bool):
            errs.append("feasibility flag must be boolean")
    if not r["disclaimer"]:
        errs.append("disclaimer present (educational framing)")
    return errs


def check_negative_cashflow(r):
    errs = []
    flags = _flags_by_code(r)
    if "CASH" not in flags:
        errs.append("critical cash-flow flag expected")
    cash_flag = next((f for f in r["risk_flags"] if f["code"] == "CASH"), None)
    if cash_flag and cash_flag["severity"] != "Critical":
        errs.append("cash-flow flag must be Critical severity")
    actions = _roadmap_actions(r)
    if not actions[0].lower().startswith("fix negative cash flow"):
        errs.append("roadmap item 1 must be the cash-flow fix")
    return errs


def check_crypto(r):
    errs = []
    flags = _flags_by_code(r)
    if "CONC" not in flags:
        errs.append("concentration flag expected")
    if "EF" not in flags:
        errs.append("emergency-fund flag expected (no emergency fund)")
    # Concentration must not be rewarded as growth: diversification metric < 80
    div = next((m for m in r["scorecard"]["metrics"] if m["name"] == "diversification"), None)
    if div and div["score"] >= 80:
        errs.append("over-concentration must not score high")
    if not any("concentrated" in i["action"].lower() for i in r["roadmap"]):
        errs.append("rebalance roadmap item expected")
    return errs


def check_offline(r):
    errs = []
    if not r["offline_mode"]:
        errs.append("offline_mode must be flagged true")
    if not r["quality_gates"]["offline_limitation_flagged"]:
        errs.append("offline limitation gate must be flagged")
    if not any(s["date"] for s in r["sources_currency"]):
        errs.append("sources must be dated")
    return errs


CHECKS = {
    "low_income": check_low_income,
    "multi_card": check_multi_card,
    "house_goal": check_house_goal,
    "negative_cashflow": check_negative_cashflow,
    "crypto": check_crypto,
    "offline": check_offline,
}


def run_all() -> dict:
    fixtures = _load_fixtures()
    results = []
    all_ok = True
    for name, raw in fixtures.items():
        profile = eng.parse_profile(raw["profile"])
        offline = raw.get("offline", False)
        report = eng.run(profile, offline=offline)
        errs = CHECKS[name](report)
        results.append({
            "scenario": name,
            "passed": not errs,
            "score": report["snapshot"]["overall_score"],
            "flags": sorted(_flags_by_code(report)),
            "errors": errs,
        })
        all_ok = all_ok and not errs
    return {"all_passed": all_ok, "results": results}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Personal Financial Planner scenario harness")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    summary = run_all()
    if args.json:
        json.dump(summary, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for r in summary["results"]:
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"[{mark}] {r['scenario']:18} score={r['score']:5} flags={r['flags']}")
            for e in r["errors"]:
                print(f"        - {e}")
        print(f"\n{'ALL PASSED' if summary['all_passed'] else 'FAILURES PRESENT'}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
