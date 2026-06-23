# Agent 可靠性 + LLM 评估

> 两块合写：**可靠性**让 agent 在 demo 现场不崩（D5/D6 必备），**评估**解决 PRD 那条"准确率 >70%"到底怎么测（验收标准）。都用 2026 当前实践（LangChain 1.0 middleware + LangSmith）。

# 第一部分：Agent 可靠性

## 核心认知：agent 比普通应用脆弱 10 倍

普通 API 调用失败 = 重试就行。agent 失败的方式多得多：LLM 幻觉、工具超时、JSON 解析错、死循环、token 烧光、限流……**不分类处理，demo 必翻车。**

## 错误四分类（可靠性地基，必考）

| 类型 | 例子 | 策略 |
|---|---|---|
| **瞬时** | 网络、429 限流、503 | **重试**（退避）|
| **LLM 可自愈** | 工具失败、JSON 不合规 | **错误回传 LLM 让它改** |
| **需人工** | 高危处置、不确定根因 | **interrupt() 暂停等人** |
| **意外 bug** | 代码异常 | **让它冒泡**，别吞 |

> 关键：**不要对所有错误都无脑重试**。`retry_on(Exception)` 是反模式——会把 401 鉴权错也死循环重试。

## 重试：指数退避 + 抖动

三层，各用各的工具：

```python
# 方式一：LangGraph 节点级重试
graph.add_node("metrics", metrics_node, retry=RetryPolicy(max_attempts=3))

# 方式二：LangChain 1.0 middleware（推荐）
from langchain.agents.middleware import ModelRetryMiddleware
llm.add_middleware(ModelRetryMiddleware(
    retry_on=(RateLimitError, APIConnectionError),
    max_attempts=3, initial_delay=1, backoff_factor=2, jitter=True,
))

# 方式三：tenacity 手写
@retry(stop=stop_after_attempt(3), wait=wait_exponential(),
       retry=retry_if_exception_type((RateLimitError,)))
def call_llm(...): ...
```

**抖动（jitter）**：±25% 随机延迟，避免多个 client 同时重试把服务打挂（thundering herd）。**只重试瞬时异常**（429/503/超时），不重试永久错（400/401）。

## 工具错误 → LLM 自愈（单条最高价值）

工具失败时**别崩**，把错误塞进 `ToolMessage` 回传，LLM 看到错误会自己改：

```python
from langgraph.prebuilt import ToolNode
tool_node = ToolNode([query_prometheus], handle_tool_errors=True)
# 工具失败 → 自动包成 ToolMessage("Error: PromQL 语法错 near...") → 回 LLM
# LLM 看到，会重新生成正确的 PromQL
```

**关键**：必须加循环上限，否则工具一直失败 → LLM 一直改 → 死循环。靠 `recursion_limit` 兜底（见下）。

## recursion_limit：防死循环

LangGraph 默认 `recursion_limit=25`（整个 run 最多跑 25 个节点）。超了抛 `RecursionError`。RCA 8 节点 × 工具循环 2-3 次 ≈ 20+，**显式设一个合理值**：

```python
app.invoke(inputs, config={"recursion_limit": 30})
```

> 没有 recursion_limit 的 agent 会在"验证→假设→验证"里无限转，烧光 token。生产级 demo **非加不可**。

## 模型降级链（可选）

主模型挂了自动切备用：

```python
llm = primary_llm.with_fallbacks([backup_llm, local_ollama_llm])
```

硅基流动主用、DeepSeek 官方备用、本地 Ollama 兜底。Demo 单 provider + 重试通常够，**周末加 Ollama 时顺手配 fallback**。

---

# 第二部分：LLM 评估（解决">70% 准确率"怎么测）

## 问题：根因不是非黑即白

"DB 连接池耗尽" 和 "连接泄漏致连接池满" 是同一个根因，但字符串匹配判不出来。**需要 LLM 当裁判**做语义判断。

## 三件套（2026 标准）

### ① 金标准数据集

为每个场景写**结构化的标准答案**（不是自由文本）：

```python
# 每条 = 输入告警 + 标准根因（结构化）
golden = [
    {
        "input": {"alertname":"MysqlSlowQueries","instance":"10.3.240.116:19211"},
        "expected": {
            "root_cause": "InnoDB 行锁竞争",      # 关键词，用于语义匹配
            "must_mention": ["行锁","innodb_row_lock"],  # 必须提到的证据
            "layer": "paas",
        }
    },
    # ... Redis OOM / ES 堆泄漏 各 5-10 条变体
]
```
**3 场景 × 5-10 变体 = 15-30 条**。这也是你的回归测试集——每次改 prompt 都重跑。

### ② LLM-as-judge（裁判模型）

用**另一个模型**（temperature=0）按 rubric 打分：

```python
class Grade(TypedDict):
    reasoning: str
    is_correct: bool   # True=根因语义命中标准答案

grader = ChatOpenAI(model="deepseek-ai/DeepSeek-V4-Flash", temperature=0)\
         .with_structured_output(Grade)

def evaluate(run) -> dict:
    output = run["output"]["report"]["root_cause"]
    expected = run["expected"]
    grade = grader.invoke(f"判断根因是否匹配。输出:{output}。标准:{expected}")
    return {"score": 1 if grade["is_correct"] else 0}
```

**裁判用便宜模型**（V4-Flash）即可，不用跟被测 agent 同款。

### ③ evaluate() 跑批 + 实验对比

```python
from langsmith import Client
client = Client()
client.evaluate(
    target_fn=run_my_agent,
    data="rca-golden-dataset",
    evaluators=[evaluate],
    experiment_prefix="prompt-v3",
)
```
每次改 prompt 跑一次，LangSmith UI 看曲线：prompt-v1 60% → v3 75%。**这才是"准确率 >70%"的证据**，评委问"你怎么知道"有据可答。

## 行为一致性（confidence 信号，可选）

同一输入跑 3 次：
- **3 次结论一致** → 高置信（研究显示 80-92% 准确）
- **3 次结论不一** → 低置信（25-60%），转人工

```python
results = [agent.invoke(input) for _ in range(3)]
if len(set(r["root_cause"] for r in results)) == 1:
    confidence = "high"   # 一致
else:
    confidence = "low"    # 分歧 → interrupt 人审
```
代价是 3× 推理。**只在最终"根因推断"节点用**，且只在准确率不够时。

---

## 速记卡

| 要点 | 内容 |
|---|---|
| 错误四分类 | 瞬时→重试 / LLM可愈→回传 / 需人→interrupt / bug→冒泡 |
| 重试 | 指数退避+抖动，**只重试瞬时异常** |
| 工具错误自愈 | handle_tool_errors=True，错误回传 LLM 自改 |
| recursion_limit | 防死循环，默认 25，显式设 |
| 金标准数据集 | 每场景 5-10 变体，结构化标准答案 |
| LLM-as-judge | 另一个模型按 rubric 判语义匹配，便宜模型即可 |
| evaluate() | 跑批 + 实验对比，证明 >70% |
| 行为一致性 | 跑 3 次，一致=高置信，分歧=转人工 |

### 比赛理论题预测

1. **Agent 常见失败模式有哪些？怎么分类处理？**（瞬时/LLM可愈/需人/bug 四类）
2. **为什么要指数退避+抖动？**（避限流+防 thundering herd）
3. **工具失败时为什么不直接崩？怎么处理？**（错误回传 LLM 让它自改 + 循环上限）
4. **怎么衡量 RCA agent 的准确率？**（金标准数据集 + LLM-as-judge + evaluate 跑批）
5. **为什么根因匹配要用 LLM judge 而非字符串匹配？**（语义等价：连接池耗尽≈连接泄漏）
6. **agent 死循环怎么防？**（recursion_limit + 行为一致性检测）

---

> **可靠性让 demo 不崩（重试+自愈+limit），评估让 >70% 可证（金标准+judge+evaluate）。** 这两块到位，agent 从"能跑"变"可信"。
