# CodeReflex · SPEC.md

---

## 1. 问题陈述

裸 LLM 写代码是"生成即停止"——它不知道自己写的代码能不能跑通、过不过测试、合不合规范。一个 coding agent 的核心价值不在"会写代码"，而在"写完能自己发现错、改对、收敛"。这要求反馈信号是**确定性代码机制**（跑测试 → 解析 → 分类 → 回灌），而非"请 LLM 自行检查"的一句提示词。

**CodeReflex** 把这条反馈闭环做成 harness 主循环的结构性脊柱：LLM 写完代码后，harness 自动跑 pytest + ruff + mypy，把失败分类成结构化反馈回灌，驱动 LLM 自我修正，直到全部通过或耗尽重试预算。失败分类法 + 收敛检测保证它有界、可测、不死循环。

**目标用户**：想要"交付能通过测试的代码"而非"交付一段代码"的开发者；以及本项目自身——harness 能 dogfood 跑自己的 pytest。

**为什么值得做**：它直接验证了 `Agent = LLM + Harness` 这一命题——当 LLM 能完成大部分"思考"时，工程师的价值落在反馈、治理、上下文这层工程上。本项目把"反馈闭环"这层工程做成可独立验证的代码，移除 LLM 后仍能单测。

---

## 2. 用户故事

遵循 INVEST 原则：

1. **[修复失败测试]** 开发者提交一个失败测试 + 任务描述，agent 写代码、跑测试、自我修正，直到测试通过或耗尽重试预算。
2. **[功能开发]** 开发者提交一个功能任务（"给 X 加 Y"），agent 写代码后自动跑 pytest+ruff+mypy 三件套，把失败结构化回灌。
3. **[收敛停机]** agent 检测到同一错误连续重复（不收敛）时，主动停机并报告"我卡在这个错误上了"，而非死循环烧 API。
4. **[危险动作审批]** 危险动作（`rm -rf`、删除项目根之外的文件、`git push --force`）被护栏拦截，WebUI 弹出审批，开发者批准/拒绝后才继续。
5. **[实时可观测]** 开发者在 WebUI 实时看到 agent 的每一步动作、测试结果、失败分类、反馈回灌，并可中途干预。
6. **[声明式配置]** 开发者通过声明式配置文件约束 agent：启用哪些校验器、重试预算、允许的路径范围、危险命令模式。

---

## 3. 领域与机制设计

coding 领域的四类机制，以及重点维度如何深入编码。所有机制均为确定性代码，移除真实 LLM 后仍可用单测验证。

### 3.1 动作 / 工具

agent 能执行的操作，每个工具是实现 `Tool` 协议的类：

| 工具 | 输入 | 行为 | 输出 |
|------|------|------|------|
| `read_file` | path | 读取目标项目文件 | 文件内容 |
| `write_file` | path, content | 写入目标项目文件 | 写入确认 |
| `list_dir` | path | 列出目录 | 条目列表 |
| `run_shell` | cmd | 执行 shell，受沙箱围栏约束 | stdout/stderr/exit_code |
| `run_validators` | — | 触发校验管线（pytest+ruff+mypy） | Feedback |

`ToolDispatcher` 按 `action.type` 路由到对应工具。全部可 mock 测试：传入构造的 Action，断言 ActionResult。

### 3.2 客观反馈信号（★ 重点深度维度）

这是本项目的 main contribution。反馈信号 = 编写的校验器 + 分类器，而非"让 LLM 自查"：

```
代码变更动作 ─► ValidatorPipeline ─► FailureClassifier ─► Feedback 对象 ─► 注入上下文
                 (pytest/ruff/mypy)    (分类法+提取)        (结构化)          (回灌LLM)
```

- **触发规则**（确定性）：`write_file` 动作执行后**自动触发** FeedbackLoop（这是 harness 的反馈机制，不依赖 LLM 主动调用）；`run_shell` 不自动触发（原始工具，结果直接回灌）；LLM 也可显式调用 `run_validators` 工具主动触发。三者共用同一 ValidatorPipeline。
- **`Validator` 协议**：`validate(project_path) -> Feedback`。三个实现：`PytestValidator`、`RuffValidator`、`MypyValidator`，各在 subprocess 跑真实工具并解析 stdout。
- **失败分类法**（深度所在）：把原始输出解析成结构化 `FailureItem`，分类为：
  - `test_failure` — 测试断言失败
  - `syntax_error` — 语法错误
  - `type_error` — mypy 类型错误
  - `lint_violation` — ruff 规范违反
  - `import_error` — 导入失败
  - `runtime_error` — 运行时异常
  
  每项提取 `file / line / message / expected / actual`。
- **收敛检测**：维护最近 N 轮的失败指纹（failure signature hash）。同一指纹连续重复 ≥ 阈值 → 判定不收敛 → 停机，报告"卡在此错误"。
- **重试预算**：硬上限 `max_retries`（配置项），耗尽即停。
- **结构化回灌**：回灌给 LLM 的是 `Feedback` 对象的文本表示（"foo.py:42 type_error: 期望 int 实际 str"），而非原始 stdout 堆。

**确定性可测**：`FailureClassifier.classify(pytest_stdout) -> [FailureItem]` 是纯函数，传入构造的 stdout 字符串，断言分类结果，每次都成立——无需真实 LLM。

### 3.3 危险动作

- `Guardrail` 策略引擎：`check(action) -> Decision(allow/intercept/deny)`
- 危险模式（可配置）：`rm -rf`、`drop`、`git push --force`、`curl|sh`、删除项目根外文件（路径穿越检测）
- 拦截后 → `HITLController` 状态机：`pending → approved | denied | timeout`，WebUI 弹审批
- 测试：`guardrail(Action(cmd="rm -rf /"))` 断言被拦截，无需 LLM

### 3.4 记忆

- **会话内**：当前 task 的动作/反馈历史（`Turn` 列表），按窗口截断注入上下文
- **跨会话**：`DecisionLog`（append-only markdown），记录 task/outcome/关键动作，按需检索而非全量载入
- 存储与检索自己实现（文件系统 + 简单关键词索引），不接框架 memory

### 3.5 六维度最低实现 + 重点

| 维度 | 最低实现 | 深度 |
|------|---------|------|
| 决策 | AgentLoop 主循环 | — |
| 工具 | ToolDispatcher + 5 工具 | — |
| 记忆 | 会话历史 + DecisionLog | — |
| 治理 | Guardrail + HITL 状态机 | — |
| **反馈** | ValidatorPipeline + Classifier | **★ 失败分类法 + 收敛检测 + 结构化回灌** |
| 配置 | 声明式 YAML 配置 | — |

---

## 4. 功能规约（按模块）

### 4.1 AgentLoop（决策主循环）
- **输入**：task 字符串、Config、Memory
- **行为**：组织上下文 → 调 LLMClient → 解析返回为 Action → Guardrail 检查 → ToolDispatcher 分发 → 若为 `write_file` 则自动触发 FeedbackLoop → 回灌 → 停机判断
- **输出**：Session（含完整 history）
- **边界**：LLM 返回非合法动作格式 → 解析器重试一次（附"请返回合法 JSON"提示），仍失败则记错误并停机；重试预算耗尽/收敛检测触发 → 停机
- **错误处理**：LLM 调用异常 → 重试 2 次后停机并报告；超时 → 中止当前轮

### 4.2 LLMClient（LLM 抽象层）
- **输入**：messages 列表、model、config
- **行为**：调 OpenAI 兼容 `/v1/chat/completions`，返回文本
- **输出**：LLMResponse(text, usage)
- **边界**：可注入 MockLLMClient（按脚本返回预设动作序列）用于离线测试
- **错误处理**：HTTP 429/5xx → 指数退避重试；key 无效 → 抛 CredentialError

### 4.3 ToolDispatcher + Tools（工具）
- **输入**：Action
- **行为**：按 type 路由到 ReadFile/WriteFile/ListDir/RunShell/RunValidators
- **输出**：ActionResult
- **边界**：路径必须在 allowed_paths 内（路径穿越检测）；RunShell 受超时限制；RunShell 命令先过 Guardrail
- **错误处理**：文件不存在 → ActionResult(success=False, error)；shell 非零退出码 → 不算 harness 错误，作为正常结果回灌

### 4.4 Guardrail + HITL（治理）
- **输入**：Action
- **行为**：匹配 dangerous_patterns → 返回 Decision(intercept)；路径穿越 → deny；否则 allow
- **输出**：Decision
- **边界**：intercept 后进 HITL 状态机 pending → approved/denied/timeout(30s)
- **错误处理**：timeout → 视为 denied

### 4.5 FeedbackLoop（★ 重点）
- **输入**：project_path、Session（含 failure_signatures）
- **行为**：跑 ValidatorPipeline → FailureClassifier 分类 → 算失败指纹 → 收敛检测 → 重试预算检查 → 生成结构化 Feedback 注入上下文
- **输出**：Feedback + continue/stop 决策
- **边界**：无失败 → Feedback(status=pass) → 停机（任务完成）；收敛 → 停机（报告卡住）；预算耗尽 → 停机
- **错误处理**：校验器自身崩溃（如 pytest 未安装）→ Feedback(status=validator_error) → 回灌让 LLM 知道

### 4.6 Memory（记忆）
- **输入**：Session、检索查询
- **行为**：会话内按窗口截断 Turn 注入上下文；跨会话读写 DecisionLog
- **输出**：上下文片段
- **边界**：窗口大小可配置；DecisionLog 按关键词检索非全量载入
- **错误处理**：DecisionLog 读写异常 → 降级为无跨会话记忆，不阻断主循环

### 4.7 Config（配置）
- **输入**：YAML 配置文件
- **行为**：加载校验器列表、重试预算、allowed_paths、dangerous_patterns、model、llm_base_url
- **输出**：Config 对象
- **边界**：缺字段用默认值；未知字段告警
- **错误处理**：文件不存在 → 用全默认值并告警；格式错误 → 抛 ConfigError

### 4.8 WebUI（界面）
- **输入**：task 提交、HITL 审批操作
- **行为**：FastAPI 提供 /submit、/approve、/deny 端点；SSE /stream 推送实时动作流
- **输出**：HTML 页面 + SSE 事件流
- **边界**：同时只支持单会话（MVP）；HITL 审批有 30s 超时
- **错误处理**：SSE 断连 → 客户端自动重连

### 4.9 CredentialStore（凭据）
- **输入**：key 名、操作（get/set/delete/status）
- **行为**：本地用 `keyring` 存 Windows Credential Manager；Docker 用环境变量；首次运行 getpass 引导录入
- **输出**：key 值（get）/ 状态（status 不回显明文）
- **边界**：status 只显示"已设置/未设置"，不回显
- **错误处理**：keyring 不可用 → 降级到环境变量并告警明文风险

---

## 5. 非功能性需求

**性能**：
- 校验器在 subprocess 跑，带超时（默认 60s），不阻塞主循环
- SSE 实时推送，动作发生后 <1s 到达浏览器
- LLM 调用指数退避重试，避免 429 雪崩

**安全（含凭据威胁模型）**：
- **威胁**：key 泄露（硬编码/提交进 git/写入日志/shell history）、路径穿越越权、危险命令破坏系统
- **对策**：key 仅存 keyring 或运行时环境变量，绝不进源码/git/日志；路径沙箱（所有文件操作限制在 allowed_paths 内，解析 `..` 穿越后拒绝）；危险命令模式拦截 + HITL；日志脱敏（正则擦除 key-like 字符串）
- **凭据威胁模型**：本地 keyring（OS 级加密，进程隔离）；Docker 环境变量（明文、进程可见——作为容器场景的已知取舍）；`.env` 仅本地开发、gitignored、明文风险写入 README

**可用性**：
- WebUI 单页面，任务提交后自动滚动展示动作流
- HITL 审批弹窗清晰显示危险动作内容 + 影响范围
- 停机时给出明确原因（通过/不收敛/预算耗尽/错误）

**可观测性**：
- 每个 Session 完整 Turn 历史可导出
- AGENT_LOG.md 记录开发过程关键节点
- SSE 流本身即实时可观测通道

---

## 6. 系统架构

```
                         ┌─────────────┐
                         │   WebUI     │  FastAPI + Jinja2 + SSE
                         │ (任务提交/  │  实时推送动作流/测试结果/HITL审批
                         │  动作流/审批)│
                         └──────┬──────┘
                                │ HTTP/SSE
                         ┌──────▼──────┐
                         │ AgentLoop   │  主循环：组织上下文→调LLM→解析动作
                         │             │  →分发→校验→回灌→停机判断
                         └──┬──┬──┬──┬─┘
            ┌───────────────┘  │  │  └───────────────┐
   ┌────────▼────────┐  ┌──────▼───────┐  ┌────────────▼─────────┐
   │ LLMClient        │  │ToolDispatcher│  │   FeedbackLoop ★     │
   │ (抽象层,可mock)  │  │              │  │ ValidatorPipeline    │
   │ OpenAI兼容API    │  │ read/write/  │  │  → FailureClassifier │
   └──────────────────┘  │ list/shell/  │  │  → 收敛检测+重试预算 │
                         │ validators   │  │  → 结构化Feedback回灌│
                         └──────┬───────┘  └──────────────────────┘
                                │
                         ┌──────▼──────┐
                         │  Guardrail  │  策略引擎：拦截危险动作
                         │  + HITL     │  状态机：pending→approved/denied
                         └─────────────┘
                                │
                         ┌──────▼──────┐
                         │   Memory    │  会话历史(Turn列表) + DecisionLog(跨会话)
                         │   + Config  │  声明式配置(YAML)
                         └─────────────┘
```

**外部依赖**：LLM 供应商（OpenAI 兼容）、pytest/ruff/mypy（校验目标项目的工具链）、目标项目文件系统。

**数据流**（一次完整反馈闭环）：
1. WebUI 提交 task → AgentLoop 构建上下文（task + memory + config）
2. LLMClient 调 LLM → 返回动作（如 `write_file`）
3. Guardrail 检查 → 危险则 HITL 暂停 → WebUI 审批
4. ToolDispatcher 执行动作 → ActionResult
5. 若动作为 `write_file` → FeedbackLoop 跑 ValidatorPipeline → FailureClassifier → Feedback
6. 收敛检测 + 重试预算判断 → 可重试则 Feedback 注入上下文回到步骤 2；否则停机
7. 全程经 SSE 推送到 WebUI

---

## 7. 数据模型

| 实体 | 关键字段 | 说明 |
|------|---------|------|
| `Action` | type, params, target_path | LLM 要执行的动作 |
| `ActionResult` | success, output, error, exit_code | 工具执行原始结果 |
| `FailureItem` | category, file, line, message, expected, actual | 单条结构化失败 |
| `Feedback` | validator, status(pass/fail), failures[], raw_output | 一次校验的结构化结果 |
| `Turn` | action, result, feedback, llm_response | 一轮交互的完整记录 |
| `Session` | id, task, history[], status, retry_count, failure_signatures[] | 一次任务会话 |
| `Config` | validators[], retry_budget, allowed_paths, dangerous_patterns, model, llm_base_url | 声明式配置 |
| `Decision` | verdict(allow/intercept/deny), reason | 护栏判定 |
| `DecisionLogEntry` | timestamp, task, outcome, key_actions[] | 跨会话记忆 |

**关键关系**：Session 1→N Turn；Turn 1→1 Action/ActionResult/Feedback；Feedback 1→N FailureItem。

---

## 8. 凭据与分发设计

### 8.1 key 存储方案

- **本地开发**：`keyring` 库 → Windows Credential Manager。首次运行 `python -m codereflex setup`，用 `getpass` 隐藏输入引导录入；`status` 只显示已设置/未设置；支持 `update` / `clear`
- **Docker 部署**：`docker run -e OPENAI_API_KEY=... ` 运行时传入，不烘焙进镜像；README 明示环境变量明文风险
- **本地开发兜底**：`.env` 文件（gitignored），`python-dotenv` 加载，README 标注明文风险

### 8.2 分发形态：Docker 镜像

- CI（GitHub Actions）里 `docker build` → 推到 GitHub Container Registry (ghcr.io)
- `docker run -p 8000:8000 -e OPENAI_API_KEY=... ghcr.io/<user>/codereflex` 一条命令启动 WebUI
- 已知限制：目标项目需挂载进容器（`-v`）；需 pytest/ruff/mypy 在容器内

### 8.3 部署

Render 或 Fly.io 免费层，跑容器暴露 WebUI 公网地址。README 说明部署架构与 CI/CD；控制成本，优先免费额度。

---

## 9. 技术选型与理由

| 选型 | 理由 |
|------|------|
| Python 3.12+ (dev: 3.14) | LLM 生态友好；pytest 可 dogfood；subprocess+pathlib 跑校验干净；asyncio 做主循环 |
| FastAPI + Jinja2 + SSE | 无 JS 构建，Docker 友好，易测；SSE 比 WebSocket 简单且够用 |
| `httpx` | 异步 OpenAI 兼容客户端，可 mock |
| `keyring` | 跨平台 OS 钥匙串抽象（Windows Credential Manager） |
| `python-dotenv` | 本地 .env 加载 |
| `pyyaml` | 声明式配置 |
| pytest | harness 自身测试 + 作为校验目标工具链 |
| Docker + GitHub Actions | 分发 + CI；CI 必含 unit-test job |
| 部署：Render/Fly.io | 免费层，容器部署，公网 URL |

**关于 Open Design**：本项目 WebUI 是开发者工具型界面（动作流 + 审批），非消费级设计重场景；选用简洁自研样式而非 Open Design 设计系统，理由是界面为功能型、构建步骤零依赖优先。

---

## 10. 验收标准

### 10.1 功能验收（实机）
- 提交一个失败测试 + 任务，agent 在重试预算内写出通过测试的代码（live demo）
- 危险动作（`rm -rf`）被护栏拦截，WebUI 弹审批，拒绝后动作不执行
- 不收敛场景（同一错误重复）→ agent 主动停机并报告"卡在此错误"

### 10.2 机制验收（mock LLM 确定性单测）
- ① `guardrail(Action(cmd="rm -rf /"))` → 断言 Decision(intercept)，无需 LLM
- ② 注入一次失败（mock LLM 先写错代码）→ FeedbackLoop 跑真实校验器 → 结构化 Feedback 回灌 → mock LLM 下一步动作改变（断言下一轮 context 含 Feedback、动作不同）
- ③ `FailureClassifier.classify(pytest_stdout_fixture)` → 断言分类为 `test_failure` 且提取出 file/line/message（重点维度行为）

### 10.3 覆盖性单测（六维度）
- AgentLoop：mock LLM 脚本驱动，断言停机条件（通过/预算耗尽/收敛）
- ToolDispatcher：构造各 Action，断言路由与路径穿越拒绝
- Guardrail + HITL：状态机 pending→approved/denied/timeout 全路径
- FeedbackLoop：pass/fail/收敛/预算耗尽四条分支
- Memory：会话窗口截断 + DecisionLog 读写检索
- Config：加载/缺字段默认/格式错误

### 10.4 工程验收
- `pytest` 一键跑全部测试，全绿
- CI（GitHub Actions）含 `unit-test` job，最后一次 pass
- `docker build` + `docker run` 一条命令起 WebUI
- 部署 URL 可访问
- 仓库零真实凭据（提交前自查 .env/history/配置）

---

## 11. 风险与未决问题

| 风险 | 对策 | 是否已决 |
|------|------|---------|
| LLM 返回非合法动作 JSON | 解析器重试一次+提示，仍失败则停机 | 已决 |
| pytest/ruff/mypy 输出格式跨版本变化 | pin 工具版本；解析器防御性编写（正则+结构化 fallback） | 已决 |
| 反馈死循环 | 收敛检测（失败指纹重复≥阈值）+ 硬重试预算 | 已决 |
| HITL 在 SSE 下的异步协调 | FastAPI 异步 + asyncio.Event 等待审批 | 已决 |
| mock LLM 测试确定性 | mock 按脚本返回预设动作序列，不引入随机 | 已决 |
| Docker 内跑目标项目校验 | 容器内预装 pytest/ruff/mypy；目标项目 `-v` 挂载 | 已决 |
| 部署免费层稳定性 | Render/Fly.io 免费层可能休眠；README 标注已知限制 | 已决 |
| **未决**：部署选 Render 还是 Fly.io | 两者都支持容器；实现时按更顺手的定 | 未决 |
| **未决**：失败分类法是否需扩展更多类别 | 先实现 6 类，实机演示后按真实失败样本决定是否加 | 未决 |
