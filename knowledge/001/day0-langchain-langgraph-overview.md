# Day 0 · LangChain / LangGraph 速览(今晚预习)

> **目标**: 今晚 1-2 小时内,搞懂 LangChain 和 LangGraph 是什么、核心概念、最小代码长什么样  
> **不要求**: 今晚代码全部跑通(明天 Day 1 才正式动手)  
> **要求**: 注册硅基流动 + 概念能看懂 + 官方文档能找到

---

## Part 1 · 注册硅基流动(10 分钟)

1. 打开 https://cloud.siliconflow.cn
2. 手机号注册(送免费额度,够学习用)
3. 左侧菜单 → 「API 密钥」→ 新建密钥 → 复制保存
4. 确认你能调通的模型:DeepSeek-V3(`deepseek-ai/DeepSeek-V3`)

> 把 API Key 存好,明天所有代码都要用。格式类似 `sk-xxxxxxxxxxxxxxxx`

---

## Part 2 · LangChain 是什么(30 分钟)

### 一句话

**LangChain 是调用 LLM 的工具箱**,把"拼 Prompt → 调 LLM → 解析输出"封装成可组合的零件。

### 开发者类比

| 你熟悉的 | LangChain 对应 |
|---|---|
| 数据库连接池 | `ChatOpenAI`(LLM 连接器) |
| SQL 模板 | `ChatPromptTemplate`(Prompt 模板) |
| 管道 / 中间件 | `Chain`(用 `\|` 串联) |
| DTO / VO | `Pydantic BaseModel`(结构化输出) |

### 4 个核心概念

#### ① LLM Wrapper — 连接大模型

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="https://api.siliconflow.cn/v1",  # 硅基流动
    api_key="sk-你的key",
    model="deepseek-ai/DeepSeek-V3",
    temperature=0  # RCA 要确定性,用 0
)

# 最简单的调用
response = llm.invoke("什么是根因分析?")
print(response.content)
```

**关键点**: `ChatOpenAI` 兼容所有 OpenAI 格式的 API(硅基流动、DeepSeek、Ollama 都兼容)。

#### ② Prompt Template — 模板化输入

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 SRE 运维专家,擅长根因分析"),
    ("user", "分析这个告警: {alert}")
])

# 填充变量
filled = prompt.invoke({"alert": "PodOOMKilled"})
print(filled)
```

**关键点**: 用 `{变量}` 占位,运行时填充。和 f-string 类似但更安全(自动转义)。

#### ③ Chain — 用管道串联

```python
# LangChain 的灵魂:用 | 把零件串起来
chain = prompt | llm

# 一行调用,自动: 填模板 → 调 LLM
result = chain.invoke({"alert": "PodOOMKilled"})
print(result.content)
```

**开发者类比**: 这就是 Unix 管道 `cat file | grep x | sort`,每个 `|` 把上一步输出喂给下一步。

#### ④ Output Parser — 解析输出

```python
from langchain_core.output_parsers import StrOutputParser

# 再加一节管道:提取纯文本
chain = prompt | llm | StrOutputParser()

result = chain.invoke({"alert": "PodOOMKilled"})
print(result)  # 直接是字符串,不是 AIMessage 对象
```

### 今晚只需记住的

```
LangChain = prompt | llm | parser
```

这就是 LangChain 的核心:**用管道把 Prompt、LLM、解析器组合起来**。

---

## Part 3 · LangGraph 是什么(30 分钟)

### 一句话

**LangGraph 是工作流编排引擎**,把多个步骤画成一张"状态机图",适合多步推理任务(如 RCA)。

### 为什么 RCA 需要 LangGraph(而不是 LangChain)

LangChain 的 Chain 是**线性的**(A → B → C)。但 RCA 是**带分支和循环的**:

```
告警 → 分析指标 → 够不够推断?
                    ├─ 够 → 出报告
                    └─ 不够 → 再查日志 → 回到推断
```

这种"条件分支 + 可能回环"的场景,Chain 搞不定,Graph 搞定。

### 开发者类比

| 你熟悉的 | LangGraph 对应 |
|---|---|
| 状态机 / 工作流引擎 | `StateGraph`(状态图) |
| 流转的数据对象 | `State`(TypedDict) |
| 每个处理步骤 | `Node`(函数) |
| 步骤间的连线 | `Edge`(边) |

### 4 个核心概念

#### ① State — 流转的数据

```python
from typing import TypedDict

class RCAState(TypedDict):
    alert: str           # 输入:告警信息
    metrics: str         # 中间:查到的指标
    root_cause: str      # 输出:根因
```

**关键点**: State 是所有节点**共享的数据载体**,每个节点读 State、改 State、传给下一个节点。

#### ② Node — 处理函数

```python
def analyze_metrics(state: RCAState) -> dict:
    """节点:分析指标"""
    alert = state["alert"]
    # 这里实际会调 Prometheus,先用 mock
    metrics = f"CPU 95%, 内存 92% (告警: {alert})"
    # 返回要更新的字段(不是整个 State,只返回变化的部分)
    return {"metrics": metrics}

def infer_root_cause(state: RCAState) -> dict:
    """节点:推断根因"""
    root_cause = f"基于 {state['metrics']},根因是内存泄漏"
    return {"root_cause": root_cause}
```

**关键点**: 每个节点是普通 Python 函数,输入 State,返回 dict(要更新的字段)。

#### ③ Graph — 组装图

```python
from langgraph.graph import StateGraph, START, END

# 创建图
graph = StateGraph(RCAState)

# 加节点
graph.add_node("analyze", analyze_metrics)
graph.add_node("infer", infer_root_cause)

# 连边(定义执行顺序)
graph.add_edge(START, "analyze")   # 开始 → analyze
graph.add_edge("analyze", "infer") # analyze → infer
graph.add_edge("infer", END)       # infer → 结束

# 编译(变成可执行的应用)
app = graph.compile()
```

#### ④ 执行

```python
# 跑起来
result = app.invoke({
    "alert": "PodOOMKilled"
})

print(result["root_cause"])
# 输出: 基于 CPU 95%, 内存 92% (告警: PodOOMKilled),根因是内存泄漏
```

### 条件分支(进阶,今晚看懂即可)

```python
def route_after_analyze(state: RCAState) -> str:
    """根据指标判断下一步"""
    if "内存" in state["metrics"]:
        return "infer_memory"
    else:
        return "infer_cpu"

graph.add_conditional_edges(
    "analyze",              # 从哪个节点出发
    route_after_analyze,    # 路由函数
    {
        "infer_memory": "infer_memory",  # 返回值 → 去哪个节点
        "infer_cpu": "infer_cpu"
    }
)
```

这就是 RCA 的核心:**根据分析结果,动态决定下一步查什么**。

---

## Part 4 · LangChain vs LangGraph 关系

```
LangChain (工具箱)              LangGraph (编排引擎)
├── ChatOpenAI (调 LLM)         ├── StateGraph (状态图)
├── PromptTemplate (模板)       ├── Node (节点函数)
├── OutputParser (解析)         ├── Edge (流转规则)
└── Tool (工具定义)             └── Checkpoint (中断恢复)
         │                              │
         └────── 两者配合使用 ──────────┘
                 LangGraph 节点内部
                 调用 LangChain 的工具
```

**RCA 智能体怎么配合**:
- LangGraph 负责画工作流(8 个节点的状态机)
- 每个 LangGraph 节点**内部**用 LangChain 调 LLM、查 Prometheus

```
LangGraph 图:
  告警接收 → 拓扑关联 → 指标分析 → 根因推断 → 报告
                           │           │
                           └─ 每个节点内部:
                              LangChain (prompt | llm) 
                              + Function Calling (查 Prometheus)
```

---

## Part 5 · 今晚验收清单

看完这份文档,你应该能回答:

- [ ] LangChain 的 Chain 是用什么符号串联的?(`|`)
- [ ] `prompt | llm` 这行代码做了什么?
- [ ] LangGraph 的 State 是干什么的?
- [ ] Node 函数的返回值是整个 State 还是部分字段?(部分)
- [ ] 为什么 RCA 用 LangGraph 而不是 LangChain?(分支/循环)
- [ ] 硅基流动的 API Key 注册好了吗?

---

## Part 6 · 官方文档(深入用)

| 资源 | 链接 | 看什么 |
|---|---|---|
| LangChain 快速入门 | https://python.langchain.com/docs/tutorials/llm_chain | 确认 `prompt \| llm` 用法 |
| LangGraph 快速入门 | https://langchain-ai.github.io/langgraph/tutorials/introduction/ | 确认 StateGraph 用法 |
| LangGraph 概念 | https://langchain-ai.github.io/langgraph/concepts/ | State/Node/Edge 详细说明 |
| 硅基流动模型列表 | https://cloud.siliconflow.cn/models | 确认可用模型 |

> **今晚不用全看**。先看本文档,有疑问再去官方文档对照。明天 Day 1 会动手写代码。

---

## 附:如果今晚想跑代码(可选)

```bash
# 装环境
python3 -m venv rca-env
source rca-env/bin/activate
pip install langchain langchain-openai langgraph

# 设环境变量(不要写进代码)
export OPENAI_API_KEY="sk-你的硅基流动key"
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1"
```

```python
# 最小测试:能跑通说明环境 OK
from langchain_openai import ChatOpenAI
import os

llm = ChatOpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    model="deepseek-ai/DeepSeek-V3"
)
print(llm.invoke("一句话解释什么是根因分析").content)
```

跑通这段 = 明天 Day 1 直接开工,不用再折腾环境。
