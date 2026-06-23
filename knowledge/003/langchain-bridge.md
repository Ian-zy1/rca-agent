# LangChain 桥:从裸 SDK 到框架

> 你 D1 的 7 个 demo 全用裸 `openai` SDK（手动拼 messages、手动 for 循环、手动 json.loads）。D3/D5 要切 LangChain/LangGraph。本文把"你今天手写的"逐个翻译成"LangChain 怎么包"，让你切换时零理解成本。读完约 20 分钟。

## 核心一句话

**LangChain 是你今天裸 SDK 代码的"脚手架"**——你手写的占位符模板、手动拼 messages、手动 tool_call 循环，它都帮你标准化成可组合的组件。**它没引入新魔法，只是把你做过的事规范化。**

---

## 对照表:你手写的 → LangChain 等价物

| 你 D1 手写的 | LangChain 等价 | 干嘛的 |
|---|---|---|
| `OpenAI(api_key, base_url)` | `ChatOpenAI(model, api_key, base_url)` | 客户端封装 |
| `f"用户问 {q}"` 手拼 messages | `ChatPromptTemplate.from_messages(...)` | 占位符模板标准化 |
| `tools=[{...}]` 手写 JSON Schema | `@tool` 装饰器 / `bind_tools([...])` | 工具定义 |
| `for tc in msg.tool_calls: ...` 手动循环 | `create_tool_calling_agent` / LangGraph 节点 | 工具循环 |
| `json.loads(r.content)` 手解析 | `with_structured_output(RCAReport)` | 结构化输出 |

---

## 模块 1 · ChatOpenAI = 你的 OpenAI client

你 D1 写的:
```python
from openai import OpenAI
client = OpenAI(api_key=..., base_url="https://api.siliconflow.cn/v1")
r = client.chat.completions.create(model="deepseek-ai/DeepSeek-V3", messages=[...])
```

LangChain 版(硅基流动照样能用,OpenAI 兼容):
```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V3",
    api_key=..., base_url="https://api.siliconflow.cn/v1",
    temperature=0,
)
resp = llm.invoke([{"role":"user","content":"解释 OOM"}])
print(resp.content)
```

**区别**:`invoke()` 替代 `create()`,返回的是 `AIMessage` 对象(有 `.content`),不是裸 dict。配置(temperature 等)放在构造时,不用每次传。

---

## 模块 2 · ChatPromptTemplate = 你的占位符模板

你 D1 学到"system=规则,user=占位符填输入"。手写是 `f"用户问 {q}"`。LangChain 把它标准化:

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 RCA 助手。按 拓扑→指标→日志→根因 流程。"),
    ("user", "{alert}"),        # 占位符
])

messages = prompt.invoke({"alert": "MySQL 10.3.240.116:19211 下单慢"})
```

**对比手写**:不用自己 `f-string` 拼了,占位符用 `{var}` 声明,变量用 `.invoke({var: value})` 填。**多轮对话、Few-shot 例子都往 from_messages 里塞**,结构清晰。

---

## 模块 3 · bind_tools = 你的 tools 定义

你 D1 手写 JSON Schema:
```python
tools = [{"type":"function","function":{"name":"query_prometheus","parameters":{...}}}]
r = client.chat.completions.create(..., tools=tools)
```

LangChain 版——把工具**绑到 llm 上**,之后每次调用自动带:
```python
from langchain_core.tools import tool

@tool
def query_prometheus(promql: str) -> str:
    """查询 VictoriaMetrics 指标,输入 PromQL 返回当前值"""
    return do_query(promql)

llm_with_tools = llm.bind_tools([query_prometheus])
resp = llm_with_tools.invoke("查 MySQL 连接数")
# resp.tool_calls → [{"name":"query_prometheus","args":{"promql":"..."}}]
```

**关键好处**:函数的**类型标注 + docstring 自动变成 JSON Schema**——不用手写 `name`/`description`/`parameters` 三件套了。D1 你手写的那坨 schema,LangChain 从函数签名直接生成。

---

## 模块 4 · with_structured_output = 你的 Pydantic 校验

你 D1 写的:`response_format={"type":"json_object"}` + `RCAReport.model_validate_json(...)`。LangChain 一行搞定:

```python
report = llm.with_structured_output(RCAReport).invoke("MySQL 锁竞争...")
# report 直接是 RCAReport 对象,不用手 json.loads
```

它内部就是帮你做了 response_format + 校验 + 重试。

---

## 模块 5 · LCEL(Runnable):组合管道

这是 LangChain 的"管道"语法,用 `|` 把组件串起来:

```python
chain = prompt | llm | parser
result = chain.invoke({"alert": "..."})
```

类比 shell 管道:`cat file | grep x | sort`。每个组件输入上一步输出。**对 RCA,8 节点工作流太复杂用管道不顺,那就要上 LangGraph(D5)。但简单两三步用 LCEL 够。**

---

## 什么时候用 LangChain,什么时候裸 SDK

| 场景 | 推荐 |
|---|---|
| D2 告警分类(单次 LLM 调用) | 裸 SDK 或 LangChain 都行,**LangChain 的 prompt 模板更整齐** |
| D3 工具封装(query_prometheus) | **LangChain `@tool`** 省手写 schema |
| D5 8 节点工作流 | **LangGraph**(LangChain 家族,状态机) |
| D6 结构化报告 | **`with_structured_output`** |

> **结论**:不用纠结"该不该学 LangChain"。**你今天裸 SDK 写的每个东西,LangChain 都有对应封装,且更省代码**。D2 起逐步替换,D5 上 LangGraph 时就天然顺了。**它不是新东西,是你做过的事的标准化。**

---

## 速记

| 要点 | 内容 |
|---|---|
| ChatOpenAI | = OpenAI client 的 LangChain 封装,`invoke()` 取代 `create()` |
| ChatPromptTemplate | 占位符模板标准化,`{var}` + `.invoke({var:val})` |
| `@tool` + `bind_tools` | 函数标注/docstring 自动生成 JSON Schema |
| `with_structured_output` | 一行搞定 response_format + Pydantic 校验 |
| LCEL 管道 | `prompt \| llm \| parser`,简单流程用,复杂用 LangGraph |
| 本质 | LangChain = 你裸 SDK 代码的脚手架,无新魔法 |

### 比赛理论题预测

1. **LangChain 解决什么问题?**(LLM 应用的标准化组件:prompt/工具/输出/链)
2. **LangChain 的 Chain 和 LangGraph 区别?**(链=线性管道;图=状态机,支持循环/分支)
3. **`@tool` 装饰器怎么工作?**(从函数签名 + docstring 自动生成 JSON Schema 给 LLM)
4. **PromptTemplate 比手拼字符串好在哪?**(占位符标准化、可复用、支持多轮/Few-shot)
