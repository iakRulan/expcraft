# 自测记录（示例，非平台正式案例）

- 日期：2026-11-19
- 输入：本地构造案例（5 个资源、2 个参数域、2 个必需对照、2 个候选方案）
- 命令：

```bash
python3 scripts/plan.py --case case.json --work .
```

## 结果摘要

| 指标 | 值 |
|-|-|
| 生成方案步骤 | 5 |
| 生成方案对照 / 参数 / 风险 | 2 / 2 / 4 |
| 生成方案总成本 / 总时长 | 2000 / 14 h |
| 生成方案校验 | valid，0 issues，2 warnings（对照未写明排除的混杂） |
| 候选 planA | invalid（缺 variables/resources/risks、缺阳性对照） |
| 候选 planB | invalid（缺元素、temperature=999 超出定义域） |
| 选中 | generated |

## 验证要点

- 参数域校验确实拦住了 `temperature=999`（>150）。
- 成本与时长由步骤数字重算，可与合同核对。
- 对照缺少 `purpose` 时给出 warning 而非误判为 valid。

> 本文件为**技能自测示例**，不冒充平台正式案例结果。
