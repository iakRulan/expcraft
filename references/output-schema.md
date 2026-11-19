# 输出字段字典

## `plan.json`

| 字段 | 说明 |
|-|-|
| `case_id` | 输入标识 |
| `goal` | 研究目标原文 |
| `hypothesis` | 可检验假设 |
| `variables[]` | `kind` / `name` / `operational_definition` / `unit` / `range` / `measurement` / `note` |
| `generated_plan` | 完整方案（见下） |
| `generated_evaluation` | 生成方案的校验结果 |
| `candidate_evaluations[]` | 每个候选方案的校验与得分 |
| `selected` | 选中方案 id |
| `ranking[]` | `id` / `score` / `valid` / `issues` / `warnings` |
| `validation_of_selected` | 选中方案的完整校验 |
| `resource_contract_used` / `parameter_domains_used` | 使用的合同与定义域 |
| `assumptions[]` | 显式假设 |

## `generated_plan`

```
hypothesis, variables[], steps[], controls[], parameters[], resources{}, risks[], assumptions[]
```

- `steps[]`：`index` / `name` / `equipment` / `duration_h` / `reagents[]` / `parameters{}` / `cost`
- `controls[]`：`type` / `purpose` / `step_index`
- `parameters[]`：`name` / `unit` / `min` / `max` / `allowed` / `source`（可选 `value`）
- `risks[]`：`failure` / `criterion` / `action` / `step_index`

## `validation.json`

`case_id` / `generated` / `candidates[]` / `selected`。

## `result.json`

| 字段 | 说明 |
|-|-|
| `case_id` / `task` / `status` | |
| `deliverables` | `plan.json` / `validation.json` |
| `counts` | `candidates` / `issues_generated` / `warnings_generated` / `controls` / `parameters` / `steps` / `risks` |
| `selected_plan` | 选中方案 id |
| `uncertainty` | 假设与限制 |
| `sources` / `changes` | |
