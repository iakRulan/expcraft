#!/usr/bin/env python3
"""plan — turn a research goal into a checkable experimental plan.

Usage:
    python3 plan.py --case /input/case.json --work /app/work

The case supplies the research goal, constraints, organizer resource/price/
booking contracts, finite parameter domains and (optionally) versioned
candidate plans. This script:

  1. parses the goal into hypothesis + variables,
  2. builds or evaluates step-by-step plans (controls, parameters, resources),
  3. computes time and cost from the resource contract,
  4. validates every plan (arithmetic, domain bounds, control coverage),
  5. writes plan.json, validation.json and result.json.

Nothing is claimed as a real lab quote or safety approval: resource numbers are
used exactly as given in the case, and every assumption is recorded.
"""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path

VERSION = "1.0.0"

REQUIRED_ELEMENTS = ["hypothesis", "variables", "steps", "controls", "parameters", "resources", "risks"]


def load(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_case(case_path: Path) -> dict:
    case_path = Path(case_path)
    if case_path.is_dir():
        return {"case_id": case_path.name, "goal": "", "raw": {}, "inputs": [str(case_path)]}
    raw = load(case_path)
    case = dict(raw) if isinstance(raw, dict) else {"value": raw}
    goal = (case.get("goal") or case.get("research_goal") or case.get("objective")
            or case.get("question") or case.get("task") or "")
    resources = case.get("resources") or case.get("resource_contract") or case.get("equipment") or {}
    domains = (case.get("parameter_domains") or case.get("parameters") or case.get("domains") or {})
    candidates = case.get("candidate_plans") or case.get("plans") or case.get("candidates") or []
    constraints = case.get("constraints") or case.get("requirements") or {}
    controls = case.get("required_controls") or case.get("controls") or []
    return {
        "case_id": case.get("case_id") or case.get("id") or case_path.stem,
        "raw": case,
        "goal": goal,
        "resources": resources if isinstance(resources, dict) else {},
        "domains": domains if isinstance(domains, dict) else {},
        "candidates": candidates if isinstance(candidates, list) else [candidates],
        "constraints": constraints if isinstance(constraints, dict) else {},
        "required_controls": controls if isinstance(controls, list) else [controls],
        "notes": case.get("notes") or "",
    }


# -- goal → hypothesis/variables -------------------------------------------

def parse_goal(goal: str):
    """Extract candidate variables and the core relationship from the goal text."""
    text = goal or ""
    variables = []
    # patterns like "effect of X on Y", "influence of X on Y", "X vs Y"
    m = re.search(r"(?:effect|influence|impact|role)\s+of\s+(.+?)\s+on\s+(.+?)(?:[.;]|$)", text, re.IGNORECASE)
    if m:
        variables.append(_var("independent", m.group(1), "自变量：目标中驱动变化的因素"))
        variables.append(_var("dependent", m.group(2), "因变量：目标中要测量的结果"))
    m2 = re.search(r"(?:compare|compare\s+the\s+effect\s+of)\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+?)(?:[.;]|$)", text, re.IGNORECASE)
    if m2:
        variables.append(_var("group", m2.group(1), "分组/处理因素"))
        variables.append(_var("group", m2.group(2), "分组/处理因素"))
    if not variables:
        # fall back to noun-ish phrases
        for phrase in re.split(r"[,;，；]", text):
            phrase = phrase.strip()
            if 2 <= len(phrase) <= 40:
                variables.append(_var("context", phrase, "从目标中析取的概念（需人工确认自变量/因变量）"))
    hypothesis = text if text else "(目标为空，需补充)"
    return hypothesis, variables


def _var(kind, name, note):
    name = re.sub(r"\s+", " ", name).strip().strip(" .")
    return {"kind": kind, "name": name, "operational_definition": "", "unit": "", "range": "",
            "measurement": "", "note": note}


# -- plan generation --------------------------------------------------------

def build_plan(case):
    """Build a plan skeleton from the goal + available resources/domains."""
    hypothesis, variables = parse_goal(case["goal"])
    resources = case["resources"]
    domains = case["domains"]

    steps = []
    idx = 0
    for key, res in (resources.items() if isinstance(resources, dict) else []):
        if not isinstance(res, dict):
            continue
        steps.append({
            "index": idx,
            "name": res.get("step") or res.get("name") or key,
            "equipment": key,
            "duration_h": res.get("duration_h") or res.get("hours") or res.get("time_h") or 0,
            "reagents": res.get("reagents") or res.get("materials") or [],
            "parameters": res.get("parameters") or {},
            "cost": res.get("cost") or res.get("price") or 0,
        })
        idx += 1
    if not steps:
        steps = [{"index": 0, "name": "实验执行", "equipment": "", "duration_h": 0,
                  "reagents": [], "parameters": {}, "cost": 0}]

    parameters = []
    for name, dom in (domains.items() if isinstance(domains, dict) else []):
        item = {"name": name}
        if isinstance(dom, dict):
            item.update({
                "unit": dom.get("unit", ""),
                "min": dom.get("min"),
                "max": dom.get("max"),
                "allowed": dom.get("allowed") or dom.get("values"),
                "source": dom.get("source") or dom.get("basis") or "",
            })
        elif isinstance(dom, list):
            item.update({"allowed": dom, "source": ""})
        parameters.append(item)

    controls = []
    for c in case["required_controls"]:
        if isinstance(c, str):
            controls.append({"type": c, "purpose": "", "step_index": None})
        elif isinstance(c, dict):
            controls.append({
                "type": c.get("type") or c.get("name"),
                "purpose": c.get("purpose") or "",
                "step_index": c.get("step_index"),
            })

    risks = [
        {"failure": "污染/交叉反应", "criterion": "阴性对照出现信号", "action": "废弃该批，回溯耗材与操作"},
        {"failure": "无信号", "criterion": "阳性对照无信号", "action": "检查试剂有效期与仪器状态，重做对照"},
        {"failure": "重复性差", "criteria": "重复样本 CV 超阈值", "action": "增加重复数，检查操作一致性", "step_index": None},
        {"failure": "样本不足", "criterion": "入组数低于方案", "action": "延长入组或调整统计功效"},
    ]

    plan = {
        "goal": case["goal"],
        "hypothesis": hypothesis,
        "variables": variables,
        "steps": steps,
        "controls": controls,
        "parameters": parameters,
        "resources": resources,
        "risks": risks,
        "assumptions": [],
    }
    return plan


# -- validation -------------------------------------------------------------

def validate_plan(plan, case):
    issues = []
    warnings = []
    arithmetic = []

    # 1. required elements
    for el in REQUIRED_ELEMENTS:
        v = plan.get(el)
        if v in (None, [], {}):
            issues.append({"check": "element", "element": el, "detail": "缺失或为空"})

    # 2. parameter domain bounds
    for p in plan.get("parameters", []):
        name = p.get("name")
        dom = (case["domains"].get(name) if isinstance(case["domains"], dict) else None)
        val = p.get("value")
        if dom is None:
            warnings.append({"check": "domain", "parameter": name, "detail": "案例未给出该参数的定义域"})
            continue
        if isinstance(dom, dict):
            lo, hi = dom.get("min"), dom.get("max")
            allowed = dom.get("allowed") or dom.get("values")
            if val is not None and lo is not None and isinstance(val, (int, float)) and val < lo:
                issues.append({"check": "domain_min", "parameter": name, "value": val, "min": lo})
            if val is not None and hi is not None and isinstance(val, (int, float)) and val > hi:
                issues.append({"check": "domain_max", "parameter": name, "value": val, "max": hi})
            if allowed and val is not None and val not in allowed:
                issues.append({"check": "domain_allowed", "parameter": name, "value": val, "allowed": allowed})
        if not p.get("source"):
            warnings.append({"check": "parameter_source", "parameter": name, "detail": "未标注参数依据（设备手册/预实验/文献）"})

    # 3. control coverage
    required = [c for c in case["required_controls"] if isinstance(c, str)] or []
    present = {c.get("type") for c in plan.get("controls", [])}
    for r in required:
        if r not in present:
            issues.append({"check": "control", "control": r, "detail": "方案缺少要求的对照类型"})
    for c in plan.get("controls", []):
        if not c.get("purpose"):
            warnings.append({"check": "control_purpose", "control": c.get("type"), "detail": "对照未说明排除哪类混杂"})

    # 4. arithmetic: recompute cost and time
    total_cost = 0.0
    total_hours = 0.0
    for s in plan.get("steps", []):
        try:
            cost = float(s.get("cost") or 0)
        except (TypeError, ValueError):
            cost = 0.0
            issues.append({"check": "cost_type", "step": s.get("index"), "detail": "成本不是数字"})
        try:
            hours = float(s.get("duration_h") or 0)
        except (TypeError, ValueError):
            hours = 0.0
            issues.append({"check": "duration_type", "step": s.get("index"), "detail": "时长不是数字"})
        total_cost += cost
        total_hours += hours
    if plan.get("total_cost") is not None:
        try:
            if abs(float(plan["total_cost"]) - total_cost) > 1e-6:
                issues.append({"check": "cost_arithmetic", "declared": plan["total_cost"], "computed": total_cost})
        except (TypeError, ValueError):
            issues.append({"check": "cost_type", "detail": "total_cost 不是数字"})
    arithmetic.append({"total_cost": total_cost, "total_hours": total_hours, "steps": len(plan.get("steps", []))})

    # 5. constraints
    cons = case["constraints"]
    if isinstance(cons, dict):
        max_cost = cons.get("max_cost") or cons.get("budget")
        if max_cost is not None and total_cost > float(max_cost):
            issues.append({"check": "budget", "computed": total_cost, "max": max_cost})
        max_time = cons.get("max_time_h") or cons.get("deadline_h")
        if max_time is not None and total_hours > float(max_time):
            issues.append({"check": "time", "computed": total_hours, "max": max_time})

    # 6. risks
    for r in plan.get("risks", []):
        if not r.get("criterion") and not r.get("criteria"):
            warnings.append({"check": "risk_criterion", "failure": r.get("failure"), "detail": "缺少判据"})
        if not r.get("action"):
            warnings.append({"check": "risk_action", "failure": r.get("failure"), "detail": "缺少处置动作"})

    return {"valid": not issues, "issues": issues, "warnings": warnings, "arithmetic": arithmetic}


def evaluate_candidate(plan, case):
    v = validate_plan(plan, case)
    score = 0
    score -= 5 * len(v["issues"])
    score -= 1 * len(v["warnings"])
    score += 2 * len(plan.get("controls", []))
    score += len(plan.get("parameters", []))
    return {"score": score, **v}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--work", required=True)
    args = ap.parse_args(argv)

    case = load_case(Path(args.case))
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    generated = build_plan(case)
    candidates = []
    for i, cand in enumerate(case["candidates"]):
        if isinstance(cand, dict):
            candidates.append({"id": cand.get("id") or f"candidate-{i+1}", **cand})

    evaluated = []
    for cand in candidates:
        evaluated.append({"id": cand.get("id"), **evaluate_candidate(cand, case)})
    gen_eval = evaluate_candidate(generated, case)

    # pick the best: highest score, valid first
    pool = evaluated + [{"id": "generated", **gen_eval, "plan": generated}]
    pool.sort(key=lambda x: ((x["valid"] is False), -x["score"]))

    out = {
        "case_id": case["case_id"],
        "goal": case["goal"],
        "hypothesis": generated["hypothesis"],
        "variables": generated["variables"],
        "generated_plan": generated,
        "generated_evaluation": gen_eval,
        "candidate_evaluations": evaluated,
        "selected": pool[0]["id"],
        "ranking": [{"id": p["id"], "score": p["score"], "valid": p["valid"],
                     "issues": len(p["issues"]), "warnings": len(p["warnings"])} for p in pool],
        "validation_of_selected": pool[0],
        "resource_contract_used": case["resources"],
        "parameter_domains_used": case["domains"],
        "assumptions": [
            "资源与价格来自组织方提供的合同/报价，不代表真实厂商报价；",
            "时间估算基于给定时长，未含排队与等待；",
            "未进行安全与伦理审查，相应内容需专家确认。",
        ],
    }
    save(work / "plan.json", out)
    save(work / "validation.json", {
        "case_id": case["case_id"],
        "generated": gen_eval,
        "candidates": evaluated,
        "selected": pool[0]["id"],
    })

    result = {
        "case_id": case["case_id"],
        "task": "experimental-plan-design",
        "status": "complete",
        "deliverables": {"plan": "plan.json", "validation": "validation.json"},
        "counts": {
            "candidates": len(candidates),
            "issues_generated": len(gen_eval["issues"]),
            "warnings_generated": len(gen_eval["warnings"]),
            "controls": len(generated["controls"]),
            "parameters": len(generated["parameters"]),
            "steps": len(generated["steps"]),
            "risks": len(generated["risks"]),
        },
        "selected_plan": pool[0]["id"],
        "uncertainty": out["assumptions"],
        "sources": [str(Path(args.case))],
        "changes": [
            {"step": "goal", "detail": f"hypothesis + {len(generated['variables'])} variables"},
            {"step": "plan", "detail": f"{len(generated['steps'])} steps, {len(generated['controls'])} controls, {len(generated['parameters'])} parameters"},
            {"step": "validate", "detail": f"{len(gen_eval['issues'])} issues, {len(gen_eval['warnings'])} warnings"},
        ],
    }
    save(work / "result.json", result)
    print(f"plan: selected={pool[0]['id']} score={pool[0]['score']} issues={len(gen_eval['issues'])} -> {work / 'plan.json'}")
    return out


if __name__ == "__main__":
    main()
