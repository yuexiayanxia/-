# CodeReflex · REFLECTION.md

## 哪些 Superpowers 技能发挥了最大作用、哪些"形式大于实质"？

**最大作用**：`brainstorming`（一次一问、多选优先、分节确认）让设计决策路径清晰可追溯；`writing-plans` 的 TDD 颗粒度（每步 2-5 分钟、完整代码、明确验证步骤）使 subagent 能零上下文执行；冷启动验证（§4.5）是全程最有价值的一环——它暴露了 4 个 brainstorming 阶段未写进 SPEC 的隐性假设（文件依赖、classifier 逻辑缺陷、Turn 默认值、版本不一致），这些是单人项目中最接近"同侪评审"的客观信号。

**形式大于实质**：`using-git-worktrees` 在本项目未实际使用——单人项目、task 间有依赖链、并行通过 subagent 而非 worktree 隔离实现。worktree 的隔离价值在多分支并行开发时才体现，而本项目的并行是"不同 subagent 写不同文件"而非"不同分支"。

## TDD 强制在 AI 协作下是阻碍还是放大器？

**放大器**。TDD 的"先红再绿"让 subagent 的实现有明确终点——测试通过即完成，不会过度工程化。冷启动验证中，subagent 严格按 TDD 执行，16 测试一次通过。但 TDD 也暴露了一个微妙问题：当测试本身有 bug（如 Task 9 缺 import），"红"可能误导——subagent 需区分"实现未写"的红与"测试写错"的红。这要求 subagent 有一定判断力，而非机械执行。

## subagent-driven 工作流能自主运行多久而不偏离？

**单个 task 内不偏离**：每个 subagent 在一个 task 内（2-5 分钟）完全自主完成，无偏离。**跨 task 需人工审核**：7 个并行 subagent 中，约 20% 产生了需要人工审核的偏差（StopIteration→RuntimeError、消息顺序、Windows 路径）。这些偏差都是"合理的适应性修正"而非"偏离主题"，但说明 subagent 会在 PLAN 代码有 bug 时自行修正——这需要人工确认修正方向正确。

## 什么样的 task 颗粒度最优？

**一个 task = 一个模块 + 一个测试文件 + 5-10 分钟**。本项目的 17 个 task 颗粒度合适：每个 subagent 一次会话完成，不跨文件依赖。太细（如"只写一个函数"）会导致 subagent 缺乏上下文；太粗（如"写整个 feedback 子系统"）会导致 subagent 偏离。Task 11（AgentLoop 集成）是最粗的 task，也是唯一需要 subagent 理解全局架构的——它恰好产生了 Windows 路径的集成问题。

## SPEC/PLAN 质量如何影响实现质量？

**具体案例**：PLAN Task 9 的 FeedbackLoop 实现用 `if not all_items:` 判定 pass/fail，但测试用 StubValidator（`validator="stub"`）的输出不被 classifier 解析（classifier 只在 `validator=="pytest"` 时跑 pytest 解析）。这导致 stub 的 FAIL 被误判为 pass，测试失败。根因是 SPEC/PLAN 未明确"classifier 只解析已知 validator 格式"这一隐含规则。subagent 修正为 `has_failure = any(f.status == FAIL for f in feedbacks)`，更鲁棒。这说明：**当 SPEC 对模块间交互的边界条件描述不足时，subagent 会在实现时撞墙并自行修正**——冷启动验证能提前暴露这类问题。

## 最有效的 prompt / context 策略是什么、为什么有效？

**给 subagent 传递"已实现模块清单 + 已知偏差"**。在 Task 11 的 prompt 中，我列出了所有已实现模块及其关键接口（如"WriteFile 接 allowed_paths 在 __init__"、"MockLLMClient 抛 RuntimeError 而非 StopIteration"、"FeedbackLoop 检查 has_failure"）。这让 subagent 不必读全部源码就能正确集成，避免了重复踩坑。有效原因：它把前序 task 的"隐性知识"显式传递给了后续 task 的 subagent。

## 凭据与分发这两条工程要求，迫使你想清楚了哪些原本会忽略的问题？

**凭据**：迫使我想清"key 在不同环境下的存储方式与威胁模型"——本地 keyring（OS 加密）vs Docker 环境变量（明文、进程可见）vs .env（明文、gitignored）。这不是"加一句提示词"能解决的，而是需要 CredentialStore 类根据环境选择后端、并在 SPEC 中明示取舍。

**分发**：迫使我想清"别人如何在一台全新机器上从零运行"——Docker 镜像需预装 pytest/ruff/mypy、目标项目需 `-v` 挂载、key 需运行时传入。这暴露了一个设计决策：harness 校验的是"目标项目"而非"自身"，所以容器内需有校验工具链 + 挂载的目标项目。

## 如果重做你会改变什么？

1. **PLAN 自检应包含"跨 task 交互"检查**：本次自检聚焦单 task 内一致性，但 Task 9 的 classifier-validator 交互问题属于跨 task，自检未覆盖。
2. **冷启动验证应更早**：在 PLAN 写完 5 个 task 后就做一次冷启动，而非等 17 个 task 全写完——能更早发现 PLAN 的系统性问题。
3. **Windows 路径应作为 Global Constraint 写进 PLAN**：反斜杠在 JSON 中的转义问题反复出现（Task 11、Task 15），应在 PLAN 中统一约定"路径嵌入 JSON 前归一化为正斜杠"。

## 对 Superpowers 方法论的批判——它假设了什么，这些假设成立吗？

**假设 1：spec 足够清晰则 subagent 不会偏离**。部分成立——单 task 内不偏离，但跨 task 交互的边界条件仍需人工审核。spec 的"完全无歧义"在实践中难以达到。

**假设 2：TDD 能保证实现质量**。成立但需补充——TDD 保证"测试通过"，但测试本身的正确性需人工审核（如 Task 9 缺 import 的测试 bug）。

**假设 3：冷启动验证能暴露 spec 缺陷**。完全成立——本次暴露的 4 个问题都是 brainstorming 阶段的隐性假设，若无冷启动会直接进入实现并放大。

**总体批判**：Superpowers 的七步工作流是有效的"流程脚手架"，它守住了 TDD、评审、计划这些纪律。但它的成本在于"前置投入"——SPEC+PLAN+冷启动占了总时间的 ~40%，而实现只占 ~30%（并行 subagent 高效）。这个比例在大型项目中更合理（spec 质量被复用多次），但在小型项目中可能过重。不过，本项目的核心命题正是"工程师的价值在 harness 这层工程"，所以这个前置投入本身就是对命题的实践。
