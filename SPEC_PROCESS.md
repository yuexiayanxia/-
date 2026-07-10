# CodeReflex · SPEC_PROCESS.md

> 记录与 Superpowers 协作生成 spec 与 plan 的过程，以及冷启动验证的客观证据。

---

## 一、brainstorming 关键节点

### 节点 1：重点维度选择

智能体追问的第一个核心问题是"六维度中选哪个作为重点深入"。这是整个项目的分水岭——它决定 harness 的性格。

智能体提供了三个选项（反馈闭环 / 治理 / 扩展），并推荐反馈闭环，理由是：coding 之所以被选为重点领域，正因反馈信号最清晰可编码；而反馈闭环是 coding agent 的灵魂（写完能自己发现错、改对、收敛）。

**我的决策**：采纳推荐，选反馈闭环。理由：它最契合"机制必须是代码"的硬判据——`FailureClassifier.classify(stdout) -> [FailureItem]` 是纯函数，移除 LLM 后仍可确定性单测。

### 节点 2：架构方案选择

智能体提出三个架构方案：
- A：反馈驱动循环（反馈是主循环脊柱）
- B：标准循环 + 校验后置（反馈是附件）
- C：事件溯源（一切皆事件）

智能体推荐 A，并指出 B"太浅"、C"偏离重点"。

**我的决策**：采纳 A。关键判断：B 的工作量与 A 相差不大但深度差很多；C 的事件存储/检索要自己实现，有过工程化风险且偏离"反馈闭环"这个重点。

### 节点 3：FeedbackLoop 触发条件

设计第 2 节呈现后，智能体自检发现一处歧义：FeedbackLoop 的触发条件"代码变更动作"不够明确——哪些动作触发？

**我的决策**：要求智能体明确化。最终规则：`write_file` 自动触发（harness 机制，不依赖 LLM 主动调用）；`run_shell` 不自动触发（原始工具，结果直接回灌）；`run_validators` 可由 LLM 显式调用。三处描述（§3.2/§4.1/§6）统一。

---

## 二、至少 3 轮关键迭代

### 迭代 1：技术栈——Python vs TypeScript

智能体推荐 Python，理由：LLM 生态友好、pytest 可 dogfood、subprocess+pathlib 跑校验干净。我确认本机有 Python 3.14 和 Node v24，两者皆可。

**处理决策**：选 Python。dogfood 能力（harness 跑自己的 pytest）是决定性因素——它让反馈闭环的自指验证成为可能。

### 迭代 2：WebUI 方案——轻量 vs 重型

作业强制要求可访问 WebUI。智能体提出三档：FastAPI+SSE 轻量 / SPA 重型 / 极简只读。

**处理决策**：选 FastAPI+SSE 轻量。理由：无 JS 构建步骤、Docker 友好、易测；HITL 审批需要交互但不需要 SPA 级复杂度。关于 Open Design（作业"强烈推荐"），在 SPEC 中说明选用自研样式而非 Open Design，理由是界面为功能型开发者工具、构建步骤零依赖优先。

### 迭代 3：失败分类法的设计深度

设计第 2 节中，智能体提出 6 类失败分类（test_failure / syntax_error / type_error / lint_violation / import_error / runtime_error）。我追问：分类器的 cross-cutting 逻辑如何处理？

**处理决策**：要求 syntax/import/runtime 作为跨校验器分类（任何输出中都扫描），而非仅限特定校验器。这一决策在冷启动验证中暴露了一个实现缺陷（见下文 §三 issue 6），后被修正。

---

## 三、冷启动验证（§4.5 — 最关键的客观证据）

### 操作方式

按 §4.5 要求，启动一个**全新 subagent session**（不导入任何先前对话或 memory），仅提供 `SPEC.md` + `PLAN.md`，指定它实现 Task 1（models）和 Task 8（classifier），并明确"遇到不确定之处即记录，而非凭猜测继续"。

### 结果

subagent 在约 15 分钟内完成两个 task，16 个测试全过。但它报告了 **6 个 spec 清晰度问题**——这些正是冷启动验证要暴露的"隐性上下文缺口"。

### 暴露的 spec 缺陷与修订

| # | subagent 报告的问题 | 严重度 | 修订 |
|---|---------------------|--------|------|
| 1 | Task 8 的文件列表缺 `feedback/__init__.py`，但测试 import `codereflex.feedback.classifier` 需要它。该文件列在 Task 7 下，只做 Task 8 的实现者会卡住。 | 高 | PLAN Task 8 文件列表加入 `feedback/__init__.py` |
| 2 | SPEC 说 "Python 3.14"，PLAN 的 pyproject.toml 写 `requires-python = ">=3.12"`，版本不一致。 | 中 | SPEC 改为 "Python 3.12+（dev: 3.14）"，与 pyproject.toml 对齐 |
| 3 | PLAN 的 commit 命令用 `cd 作业`，但实际 git 仓库根在上一层。工作目录歧义。 | 低 | 后续 task 实现时统一从仓库根用 `作业/`-前缀路径 |
| 4 | `Turn` dataclass 四个字段无默认值，无法增量构造。SPEC §7 说 Turn 是"一轮完整记录"，但实现中需要逐步填充。 | 中 | Turn 四字段加 `= None` 默认值（代码已修） |
| 5 | `failure_signature` 用 MD5，SPEC/PLAN 未说明是否需抗碰撞。 | 低 | 确认为去重用途（非安全），可接受，SPEC 不改 |
| 6 | **分类器 cross-cutting 逻辑有隐含优先级**：`if not items` 守卫导致 pytest 输出同时含 test_failure 和 runtime traceback 时，runtime 信号被丢弃。这一优先级规则在 SPEC 中未文档化。 | **高** | 移除 `if not items` 守卫，runtime 始终检查；`_RUNTIME` 正则加负向先行排除 SyntaxError/ImportError 防止双重分类（代码已修） |

### 产出与预期差距

- **预期**：subagent 能按 PLAN 逐步实现，测试通过。
- **实际**：功能实现成功（16 测试全过），但暴露了 2 个高严重度问题（#1 文件依赖、#6 分类器逻辑缺陷）和 2 个中严重度问题（#2 版本不一致、#4 Turn 默认值）。
- **差距分析**：问题 #1 和 #2 是"文档一致性"类——在多 task 交叉引用时容易遗漏。问题 #4 和 #6 是"设计隐含规则"类——brainstorming 阶段讨论过但未写进 SPEC 的细节。这正是冷启动验证的价值：**它暴露了我和主 agent 在 brainstorming 中沉淀的、未明文写下的隐性假设**。

### 据此对 SPEC/PLAN 的修订（关键 diff）

1. **PLAN Task 8 文件列表**：`Create: 作业/codereflex/feedback/classifier.py` → 增加 `Create: 作业/codereflex/feedback/__init__.py`
2. **SPEC §9 技术选型**：`Python 3.14` → `Python 3.12+ (dev: 3.14)`
3. **PLAN Task 1 models.py**：`Turn` 四字段加 `= None`
4. **PLAN Task 8 classifier.py**：`if not items: items.extend(...runtime...)` → `items.extend(...runtime...)`（移除守卫）；`_RUNTIME` 正则加 `(?!SyntaxError|ImportError)`

---

## 四、AI 建议 vs 用户决策

| 建议 | 来源 | 决策 | 理由 |
|------|------|------|------|
| 重点维度选反馈闭环 | AI 推荐 | 采纳 | 最契合"机制是代码"硬判据 |
| 架构方案 A（反馈驱动） | AI 推荐 | 采纳 | B 太浅，C 偏离重点 |
| 技术栈选 Python | AI 推荐 | 采纳 | dogfood 能力是决定性因素 |
| WebUI 选 FastAPI+SSE 轻量 | AI 推荐 | 采纳 | 无 JS 构建、Docker 友好 |
| 用 Open Design | 作业"强烈推荐" | 推翻 | 界面为功能型开发者工具，自研样式更合适，SPEC 说明理由 |
| FeedbackLoop 触发规则明确化 | AI 自检发现 | 采纳 | 消除歧义 |
| 分类器 cross-cutting 逻辑 | AI 提出 | 修正 | 冷启动暴露缺陷后修正为始终检查 |
| Turn 加默认值 | 冷启动 subagent 报告 | 采纳 | 支持增量构造 |
| runtime 正则排除 Syntax/Import | 冷启动修正 | 采纳 | 防止双重分类 |

---

## 五、反思

**brainstorming 做得好的地方**：
- 一次一个问题、多选优先的方式，让决策路径清晰、可追溯。
- 智能体自检发现 FeedbackLoop 触发歧义，说明自检环节有效。
- 分节呈现设计、逐节确认，避免了"一次性 dump 大文档、用户无法审"的问题。

**brainstorming 让我不满的地方**：
- cross-cutting 分类逻辑的优先级规则在讨论中隐含但未写进 SPEC，直到冷启动才暴露。说明 brainstorming 的"口头共识"需要更积极地写进文档。
- Task 间文件依赖（`__init__.py`）在 PLAN 中跨 task 引用但未显式标注，冷启动实现者会卡住。说明 PLAN 的 per-task 文件列表应自包含。

**冷启动验证的价值**：它是单人项目中最接近"同侪评审"的机制。一个全新 agent 在每个未明文写下的假设处受阻——这些受阻之处恰是 spec 质量最有价值的反馈信号。本次验证暴露的 4 个可操作问题（#1/2/4/6），在正式实现前修正，避免了后续 15 个 task 重复踩坑。
