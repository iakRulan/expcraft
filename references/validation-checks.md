# 校验检查项

`validate_plan(plan, case)` 返回 `{valid, issues[], warnings[], arithmetic[]}`。`issues` 非空即 `valid=false`。

## 结构性

| check | 触发 | 级别 |
|-|-|-|
| `element` | `hypothesis`/`variables`/`steps`/`controls`/`parameters`/`resources`/`risks` 缺失或为空 | issue |
| `control` | 缺少案例要求的对照类型 | issue |
| `control_purpose` | 对照未说明排除哪类混杂 | warning |

## 参数

| check | 触发 | 级别 |
|-|-|-|
| `domain_min` | 值 < 定义域下界 | issue |
| `domain_max` | 值 > 定义域上界 | issue |
| `domain_allowed` | 值不在允许集合内 | issue |
| `parameter_source` | 未标注参数依据（设备手册/预实验/文献） | warning |
| `domain` | 案例未给出该参数定义域 | warning |

## 算术与约束

| check | 触发 | 级别 |
|-|-|-|
| `cost_type` | 步骤成本或 `total_cost` 非数字 | issue |
| `duration_type` | 时长非数字 | issue |
| `cost_arithmetic` | 步骤成本之和 ≠ 声明的 `total_cost` | issue |
| `budget` | 总成本超过 `constraints.max_cost`/`budget` | issue |
| `time` | 总时长超过 `constraints.max_time_h`/`deadline_h` | issue |

## 风险

| check | 触发 | 级别 |
|-|-|-|
| `risk_criterion` | 失败模式缺少判据 | warning |
| `risk_action` | 失败模式缺少处置动作 | warning |

## 排序规则

候选方案排序键：`valid=false` 优先排后；然后按 `score` 降序。

```
score = 2·controls + parameters − 5·issues − 1·warnings
```

## 假设声明（写入输出）

1. 资源与价格来自组织方提供的合同/报价，不代表真实厂商报价；
2. 时间估算基于给定时长，未含排队与等待；
3. 未进行安全与伦理审查，相应内容需专家确认。
