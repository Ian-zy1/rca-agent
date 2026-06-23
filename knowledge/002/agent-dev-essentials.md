# Agent 工程必备:结构化输出 + 部署

> 本文补 002 知识库的工程层缺口:LLM 输出怎么变成代码能用的数据,以及 agent 怎么从脚本变成在线服务。对应 D2(模型定义)/D6(API+部署)。

## 模块 1 · Pydantic 结构化输出

### 问题:LLM 输出是散装文本

LLM 默认返回一段文字。你想要 `report.root_cause` 能当变量用,得先解析 JSON 再校验字段——裸 `json.loads` 等于不设防,模型漏字段或类型乱来时,bug 会藏到很深的地方才爆。

### Pydantic BaseModel:让类型标注变成强制规则

Python 的类型标注(`x: str`)本身**运行时不检查**。继承 `BaseModel` 后,标注变成**真实验证的契约** + 自动获得 validate/dump/schema 工具箱:

```python
from pydantic import BaseModel

class RCAReport(BaseModel):
    root_cause: str
    confidence: float
    evidence: list[str]
    suggestion: str | None = None
```

### 三个核心方法

| 方法 | 作用 | 何时用 |
|---|---|---|
| `model_validate_json(str)` | JSON 字符串 → 对象(验证+解析+构造) | 吃 LLM 输出 |
| `model_dump()` | 对象 → dict | 存库 / 返回 API |
| `model_json_schema()` | 导出 JSON Schema | 直接当 FC 工具的 parameters |

### 让 LLM 强制输出可解析 JSON

光在 prompt 里说"输出 JSON"不可靠。用 OpenAI 兼容的 `response_format`:
```python
r = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3",
    messages=[...],
    response_format={"type": "json_object"},
)
report = RCAReport.model_validate_json(r.choices[0].message.content)
```

### 安全转换(对 LLM 输出特别友好)

`confidence: float` 接受 `0.9` / `9`(int→float) / `"0.9"`(数字串→float),只有 `"很高"` 这种才报错。LLM 常把数字写成字符串,Pydantic 默默转好——这是它比裸 json.loads 强的关键。

### 字段必填 vs 可选

- 没默认值 = **必填**,漏了就 ValidationError
- 给默认值(`= None` / `= []`)= **可选**

> **一句话:BaseModel 把"散装 JSON"验收成类型化对象,在 LLM 和业务代码之间当边界守卫。过了 model_validate_json 这行,`report.root_cause` 就保证是 str。**

---

## 模块 2 · Agent 部署:从脚本到在线服务

### 核心认知:agent 部署 = 普通后端部署

agent 不是模型、不是框架,就是**一段调 LLM 的 Python 代码**。部署它 = 把这段代码包进 web 服务长驻,和部署任何 FastAPI 后端一模一样,**没有任何特殊性**。

### 三步演化

**① 脚本 → 函数**:把 demo 的顶层逻辑包成可传参的函数
```python
def run_rca(alert_text: str) -> RCAReport:
    messages = [{"role": "system", ...}, {"role": "user", "content": alert_text}]
    # demo_agent 里那段 tool_call 循环
    return report
```

**② 函数 → web 服务**(FastAPI 包一层,这就是"部署 agent"):
```python
from fastapi import FastAPI
app = FastAPI()

@app.post("/api/chat")
def chat(req: dict):
    return {"report": run_rca(req["message"]).model_dump()}

@app.post("/api/alerts")
def alerts(webhook: dict):
    return {"report": run_rca(parse_alertmanager(webhook)).model_dump()}
```

**③ 长驻**(一条命令上线):
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
agent 就一直在监听 8000 端口,谁 POST 过来就处理。Alertmanager webhook 指过来、前端发请求过来——**agent 就"部署"完了**。这就是 D6 的全部。

### 三个"部署"千万别混

| 部署什么 | 干啥 | 本项目对应 |
|---|---|---|
| 部署 LLM(大模型部署) | 本地跑模型权重(vLLM/Ollama) | Oracle 标的失分点;周末可选补 |
| **部署 agent(本文)** | **FastAPI 包编排代码,长驻接请求** | **D6,最简单** |
| 部署框架(UModel) | 跑框架自己的服务 | 不做 |

LLM 是云 API(硅基流动,别人部署好了),你只部署"调它的编排代码"——所以 agent 部署是三种里最简单的。

### agent 比普通后端多考虑的一点:慢

一次 RCA 要调多次 LLM(10-30 秒)。应对:
- **async**:`async def` + `await client.chat.completions.create(...)`,别阻塞工作线程
- **streaming**(SSE):前端看到字一个个出来,正好对应 PRD"展示 RCA 推理过程"
- **异步队列**:webhook 先回 200,后台跑完存 DB,前端轮询 `/api/reports/{id}`

> **一句话:agent 部署 = FastAPI 包编排代码 + uvicorn 长驻。唯一额外考虑是它慢——用 async / streaming / 异步队列。**

---

## 速记卡

| 要点 | 内容 |
|---|---|
| `BaseModel` | 激活类型强制 + 工具箱(validate_json / dump / schema) |
| `response_format` | `{"type":"json_object"}` 强制 LLM 输出合法 JSON |
| 安全转换 | int→float、"0.9"→float 自动;只有不兼容才报错 |
| agent 部署 | FastAPI + uvicorn,无特殊性 |
| agent 慢 | async + streaming(SSE) + 异步队列 |
| 三种部署别混 | LLM(vLLM/Ollama) / agent(FastAPI) / 框架(UModel) |

### 比赛理论题预测(工程向)

1. **Pydantic 在 LLM 应用里干什么?**(把 LLM 散装输出验收成类型化对象,边界校验)
2. **怎么让 LLM 稳定输出 JSON?**(response_format + Pydantic 校验 + 重试)
3. **Agent 怎么部署?和普通 web 服务有啥区别?**(FastAPI 包一层长驻;本质没区别,就是慢,要 async/streaming)
4. **为什么 agent 要用流式输出?**(UX + 长输出不超时 + 推理过程可见)
