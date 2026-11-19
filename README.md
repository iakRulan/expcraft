# expcraft — 实验方案生成与优化 Skill

把研究目标变成一份**能排期、能执行、能被同行评审**的实验方案：假设与可操作变量、对照及其排除的混杂、绑定设备/试剂/参数范围的步骤、时间与成本估算、失败模式与止损点。

## 解决什么问题

普通 Agent 的常见失败：复述目标；步骤写成教科书目录；变量只有名字没有操作定义；对照只有空白组；参数不写量程与单位；设备耗材不落型号；时间与预算缺失；风险只写"注意安全"。

## 安装与依赖

- Python 3.9+，仅标准库
- 无需联网

```
expcraft/
├── SKILL.md
├── README.md
├── GITHUB_URL.txt
├── references/
│   ├── validation-checks.md
│   └── output-schema.md
├── examples/
│   ├── case.example.json
│   └── selftest-summary.md
└── scripts/
    └── plan.py
```

## 用法（最小示例）

```bash
python3 scripts/plan.py --case /input/case.json --work /app/work
```

输入示例：

```json
{
  "case_id": "demo",
  "goal": "Effect of annealing temperature on the conductivity of perovskite films",
  "constraints": {"max_cost": 5000, "max_time_h": 80},
  "resources": {
    "tube_furnace": {"step": "退火", "duration_h": 4, "cost": 400}
  },
  "parameter_domains": {
    "temperature": {"unit": "C", "min": 80, "max": 150, "source": "预实验"}
  },
  "required_controls": ["blank", "positive"]
}
```

> 以上为**示意示例**，不是正式案例结果。

## 输出

| 文件 | 内容 |
|-|-|
| `plan.json` | 生成的方案、候选方案评估、选中方案、排序、合同与假设 |
| `validation.json` | 校验明细（issues / warnings / 算术） |
| `result.json` | `case_id` / `status` / counts / selected_plan / uncertainty |

## 关键设计

- **合同驱动**：步骤来自资源合同，成本/时长由合同数字计算。
- **域校验**：参数必须落在案例给出的有限定义域内。
- **对照要有用**：每个对照必须说明排除哪类混杂。
- **算术可核**：成本与时间由步骤重算，不一致即判无效。
- **风险有判据与止损**。
- **假设显式**：资源数字来自合同，不声称真实报价或安全审批。

## 局限

- 变量操作定义依赖目标文本与模型补充；
- 风险预案为通用模板 + 案例约束，不替代实验室安全评估；
- 不进行文献综述与统计建模。

## 许可与版本

- 版本：expcraft 1.0.0
- 纯 Python 标准库。
