---
name: expcraft
description: "Turn a research goal into a checkable experimental plan: hypothesis and operationalized variables, controls with stated purposes, steps bound to equipment/reagents/parameters, time and cost arithmetic from a resource contract, parameter-domain checks, risk/failure modes with criteria and stop-rules. Trigger on: '实验方案', '实验设计', '方案优化', 'experiment design', 'protocol design', 'design of experiments', '排期', '成本估算'. Not for: literature review, data modelling, paper writing, or replacing safety/ethics review."
---

# expcraft — Experimental Plan Generation and Validation

> **脚本路径**：本技能安装于 `/skills/weekly-skill/`，脚本绝对路径为 `/skills/weekly-skill/scripts/`（工作目录是 `/app/work`，不要用相对路径）。

Turn a research goal into a plan a lab can schedule, execute and review — and prove the arithmetic. The failure mode this skill exists to prevent: a textbook-shaped outline ("准备样品—设置对照—检测分析—统计分析") with no operational definitions, no positive control, no parameter ranges, no equipment models, no cost/time estimate, and a single "注意安全" for risk.

**Method in one line:** parse the goal into hypothesis + variables → bind steps to the case's resource contract → compute time/cost → validate domains, controls, arithmetic and risks → emit the plan with a validation verdict.

## When to use

- Input: a case file (default `/input/case.json`) with the research goal, constraints, resource/price contract, parameter domains, required controls, and optionally versioned candidate plans.
- Output: under `/app/output` — `plan.json`, `validation.json`, `result.json`.
- Resource numbers are used **exactly as given**; the plan never claims a real vendor quote or safety approval.

## Pipeline (run in order)

### Phase 1 — Generate / evaluate plans

```bash
python3 /skills/weekly-skill/scripts/plan.py --case /input/case.json --work /app/work
```

1. **Goal → hypothesis + variables.** Recognizes `effect of X on Y`, `compare A and B`; falls back to phrase extraction. Each variable carries kind (independent/dependent/group/context) and a note; operational definitions are filled by the model where the goal does not state them.
2. **Build a plan** from the resource contract: each resource becomes a step with `duration_h`, `cost`, `reagents`, `parameters`. Controls come from `required_controls`. Parameter domains become `parameters[]` with `unit`, `min`, `max`, `allowed`, `source`.
3. **Evaluate candidate plans** (if the case provides versioned plans) with the same validator, then rank: valid plans first, then by score (controls + parameters − issues/warnings).

### Phase 2 — Validate (built in)

Every plan is checked for:

| Check | Content |
|-|-|
| `element` | hypothesis / variables / steps / controls / parameters / resources / risks all present |
| `domain_min` / `domain_max` / `domain_allowed` | parameter values inside the case's finite domain |
| `control` | every required control type present |
| `control_purpose` | each control states which confounder it removes |
| `parameter_source` | parameter basis (设备手册 / 预实验 / 文献) stated |
| `cost_type` / `cost_arithmetic` | step costs numeric and their sum equals `total_cost` |
| `duration_type` | durations numeric |
| `budget` / `time` | totals within the case constraints |
| `risk_criterion` / `risk_action` | every failure mode has a criterion and an action |

The validator recomputes cost and time from step-level numbers — a plan whose totals do not add up is invalid, not just noted.

### Phase 3 — Report

`plan.json` contains the generated plan, the generated evaluation, per-candidate evaluations, the selected plan id, the ranking, the resource/domain contracts used, and explicit assumptions. `result.json` carries `case_id`, `status`, counts, `selected_plan`, `uncertainty`, `sources`, `changes`.

Copy to `/app/output`:

```bash
mkdir -p /app/output
cp /app/work/plan.json /app/work/validation.json /app/work/result.json /app/output/
```

## Rules that must hold

1. **No generic steps.** Every step binds to an equipment id from the resource contract; unbound steps are flagged.
2. **Controls have a job.** Each control states which confounder it removes; a single blank control is reported as a warning.
3. **Parameters have domains and provenance.** Value + unit + allowed range + basis (手册/预实验/文献); out-of-domain values invalidate the plan.
4. **Arithmetic must add up.** Cost and time are recomputed from steps; mismatch is an issue.
5. **Risks have criteria and stop-rules.** Failure mode → detection criterion → action → (optionally) the step it belongs to.
6. **Assumptions are explicit.** Resource numbers are contract data, not real quotes; no safety or ethics approval is implied.

## Exception handling

| Situation | Behaviour |
|-|-|
| Goal empty | hypothesis recorded as "(目标为空，需补充)"; variables extracted as context phrases |
| No resource contract | a single placeholder step; element/resource warnings |
| Parameter without domain | warning `domain` (案例未给出定义域) |
| Candidate plan missing keys | element issues; still ranked (lowest) |
| Cost/time not numeric | `cost_type` / `duration_type` issue, value treated as 0 |
| Constraints absent | budget/time checks skipped |

## Self-check

```bash
python3 -c "import json;v=json.load(open('/app/work/validation.json'));print(v['selected'], [ (x['id'],x['valid'],x['score']) for x in v['candidates']])"
python3 -c "import json;r=json.load(open('/app/work/result.json'));print(r['case_id'], r['status'], r['counts'])"
```

The selected plan must be `valid: true` (or the selection must be explained in `result.json.uncertainty`).