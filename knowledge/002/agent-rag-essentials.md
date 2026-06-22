# Agent 与 RAG 理论必备速览

## 模块 1 · Agent 设计模式:ReAct / Plan-and-Execute / Reflection / ToT

### 核心概念

**Agent = LLM + 工具 + 自主决策 + 循环**。LLM 是大脑,工具是手脚,Agent 是完整的"人"——能根据环境反馈决定下一步做什么。

**与普通 Chain 的本质区别**:Chain 是预先定义的管道(`prompt | llm | parser`),Agent 是**循环 + 条件分支**——模型自己决定何时调工具、何时停下、何时换思路。

### 4 种主流设计模式

#### ① ReAct(Reasoning + Acting)— 最经典

**循环**:Thought(想)→ Action(做)→ Observation(看结果)→ Thought → ...

**例子**(RCA 场景):
```
Thought: 用户问"为什么 order-service 慢"。我需要先查指标。
Action: query_prometheus("rate(http_request_duration_seconds_sum{service='order-service'}[5m])")
Observation: P95 延迟从 200ms 涨到 1800ms
Thought: 延迟涨了 9 倍,可能下游慢。查依赖的 MySQL。
Action: query_prometheus("mysql_global_status_slow_queries")
Observation: 慢查询从 5/min 涨到 80/min
Thought: MySQL 慢查询暴涨,可能是根因。但要看日志确认。
Action: query_loki('app="order-service" AND level="error"')
Observation: "HikariPool-1 - Connection is not available"
Thought: 连接池耗尽,慢 SQL 占满连接。可以下结论了。
Final Answer: 根因是 MySQL 慢 SQL 占满连接池...
```

**优势**:灵活、可解释(每步思考可见)。**劣势**:容易绕圈子(死循环)、token 消耗高。

#### ② Plan-and-Execute — 状态机式

**流程**:
1. **Planner**:一次性生成完整计划(拆成 N 步)
2. **Executor**:按计划逐步执行
3. **Re-planner**:执行中发现偏差,重新规划

**LangGraph 是这个模式的工程化实现**——把计划显式画成状态图,每个节点是一步。

**对比 ReAct**:Plan-and-Execute 更可控、易调试,但灵活性差。

#### ③ Reflection(自我反思)

**机制**:完成任务后,让另一个 LLM(或同一 LLM)评估自己的回答,发现问题后重新生成。

**例子**:
```
1. LLM 生成根因报告
2. Reflector LLM 评估: "这个根因没考虑网络因素,证据不够"
3. 原模型根据反馈,补充网络查询,重写报告
```

**适合**:高质量要求场景(医疗/法律/RCA 报告)。**代价**:多花一倍 token。

#### ④ Tree of Thoughts(思维树)

**机制**:每步生成多个候选 → 评估打分 → 选最优路径继续。树形搜索(BFS/DFS)。

**适合**:复杂数学/谜题。**不适合**:RCA(故障排查不需要多路径)。

### RCA 智能体选型建议

| 维度 | 推荐 |
|---|---|
| Demo 一周内做完 | **Plan-and-Execute(LangGraph 状态机)** |
| 灵活应对未知故障 | ReAct |
| 报告质量优先 | Plan-and-Execute + Reflection |
| 多路径探索 | 不需要(故障根因通常单一) |

**结论**:RCA Demo 选 **Plan-and-Execute**,用 LangGraph 画 8 节点状态图(001 PRD 已设计)。周末如有空加 Reflection 提升报告质量。

### 一句话总结

> **Agent 的本质是 LLM + 循环 + 工具。ReAct 是"边想边做"的经典模式,Plan-and-Execute 是"先规划后执行"的状态机模式。RCA 用后者(LangGraph)——可控、可调试、可演示。**

---

## 模块 2 · Function Calling 与 Tool Use 协议

### 核心概念

**Function Calling**:你把函数签名(用 JSON Schema 描述)告诉 LLM,LLM **自己决定**调不调、调哪个、传什么参数。

**关键澄清**:LLM **不执行**函数,它只返回"请帮我调用 query_prometheus,参数是 XXX"。**执行在你的代码里**——LLM 是决策者,你是执行者。

### 完整调用流程(5 步)

```
1. 用户提问
   ↓
2. LLM 看到 tools 定义 + 用户问题,返回 tool_call:
   {name: "query_prometheus", args: {query: "rate(...)[5m]"}}
   ↓
3. 你的代码接收 tool_call,真正调用 query_prometheus 函数
   ↓
4. 把结果作为 tool_response 回传 LLM:
   "结果: P95 = 1800ms"
   ↓
5. LLM 基于结果继续生成(可能再调工具,或给最终答案)
```

### tools 参数的 JSON Schema

OpenAI 协议规定 tools 是一个数组,每个元素长这样:

```json
{
  "type": "function",
  "function": {
    "name": "query_prometheus",
    "description": "查询 Prometheus 指标,输入 PromQL 返回当前值",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "PromQL 查询语句"
        },
        "range": {
          "type": "string",
          "description": "时间范围,如 5m / 1h"
        }
      },
      "required": ["query"]
    }
  }
}
```

**三个必填字段**:`name`(函数名)/ `description`(做什么,LLM 据此决定何时调)/ `parameters`(JSON Schema 参数定义)。

### description 的写法决定智能程度

**差的 description**:"查询 Prometheus"——LLM 不知道何时调、能查什么。
**好的 description**:"查询 Prometheus 时序数据库,获取 CPU/内存/网络/QPS/延迟等运行时指标。输入 PromQL 语句(如 rate(http_requests_total[5m])),返回数值。**当需要确认指标数值时调用此工具。**"

**法则**:写得像 API 文档的 README,**明确说明何时该调**。

### Function Calling vs ReAct

| 维度 | Function Calling | ReAct |
|---|---|---|
| 谁决定调工具 | LLM(通过结构化 tool_call) | LLM(通过文本输出 Action: ...) |
| 协议 | 官方 JSON Schema 标准 | 文本解析(早期) |
| 多步 | 单步,需循环封装 | 原生循环 |
| 错误处理 | tool_response 返错误,LLM 自处理 | Observation 直接看错误 |

**实战**:LangChain Agent 默认是 ReAct 模式 + Function Calling 协议(混合)。LangGraph 用状态图实现循环。

### MCP(Model Context Protocol)

Anthropic 2024 年提出的**标准化 AI 访问工具/数据**的协议。

**类比**:OpenAPI/Swagger,但 for AI Agent。一份 MCP server 描述,所有兼容的 AI 都能用。

**现状**:阿里 sysom_mcp / ack-mcp-server 已支持,OpenAI 2025 年也宣布支持。**未来趋势**,但 RCA Demo 一周内不必用——直接 Function Calling 更简单。

### 一句话总结

> **Function Calling = LLM 决策 + 你执行。把工具的 name/description/parameters(JSON Schema)告诉 LLM,LLM 返回 tool_call,你执行后回传结果。description 写得好 = Agent 智能程度高。**

---

## 模块 3 · Embedding 与向量化原理

### 核心概念

**Embedding(嵌入)**:把文本映射成高维浮点向量(典型 768/1024/1536/3072 维)。**语义相似的文本 → 向量距离近**。

**为什么能做语义搜索**:
```
文本: "Pod 内存溢出"   → [0.12, -0.34, 0.56, ...] (1024 维)
文本: "OOMKilled"      → [0.15, -0.31, 0.52, ...] (1024 维)
文本: "MySQL 慢查询"   → [-0.45, 0.22, -0.18, ...] (1024 维)

余弦相似度:
  "Pod 内存溢出" vs "OOMKilled"     = 0.89  (高,同义)
  "Pod 内存溢出" vs "MySQL 慢查询"  = 0.12  (低,无关)
```

**SQL like 搜不到的,向量能搜到**——这就是 RAG 的基础。

### 训练原理(简化版)

Embedding 模型训练目标:**拉近相似句对,推远不相似句对**。

**训练数据**(对比学习):
```
正样本对: ("Pod 内存溢出", "容器 OOMKilled")
负样本对: ("Pod 内存溢出", "MySQL 连接失败")
```

模型学到的:**语义相似 ≠ 字面相似**。

### 维度选择

| 维度 | 精度 | 速度 | 成本 | 适用 |
|---|---|---|---|---|
| 384 | 中 | 最快 | 最便宜 | 简单分类 |
| 768 | 较高 | 快 | 便宜 | 中等规模(10万文档) |
| **1024** | **高** | **中** | **中** | **RCA 推荐(平衡)** |
| 1536 | 很高 | 较慢 | 较贵 | OpenAI ada-002 |
| 3072 | 极高 | 慢 | 贵 | OpenAI text-embedding-3-large |

**RCA 选 bge-m3(1024 维)**:中文好,硅基流动免费,1024 维够用。

### 主流 Embedding 模型

| 模型 | 维度 | 中文 | 价格 |
|---|---|---|---|
| **bge-m3**(硅基流动推荐) | 1024 | ⭐⭐⭐⭐⭐ | 免费(硅基流动额度) |
| bge-large-zh-v1.5 | 1024 | ⭐⭐⭐⭐⭐ | 免费(本地部署) |
| OpenAI text-embedding-3-small | 1536 | ⭐⭐⭐ | $0.02 / 1M token |
| OpenAI text-embedding-3-large | 3072 | ⭐⭐⭐⭐ | $0.13 / 1M |
| M3E-large | 1024 | ⭐⭐⭐⭐ | 免费(本地) |

### 调用方式

```python
from openai import OpenAI
client = OpenAI(base_url="https://api.siliconflow.cn/v1", api_key="sk-xxx")

resp = client.embeddings.create(
    model="BAAI/bge-m3",
    input=["Pod 内存溢出", "OOMKilled", "MySQL 慢查询"]
)
# resp.data[0].embedding → [0.12, -0.34, ...] 长度 1024
```

### Embedding 的局限

| 问题 | 解释 | 应对 |
|---|---|---|
| 数字/日期不准 | "2024 年故障"和"2023 年故障"向量很近 | 用 metadata 过滤 |
| 长文档信息丢失 | 把 5000 字文档压成 1024 维向量,细节被抹掉 | **Chunking 切分**(下一模块) |
| 跨语言漂移 | 中英文混合时向量不准 | 选多语言模型(bge-m3 支持) |
| 否定语义弱 | "是故障"和"不是故障"向量很近 | 不靠向量,靠 LLM 生成 |

### 一句话总结

> **Embedding 把文本变成 1024 维向量,语义相似的向量靠近。bge-m3 是中文最佳免费选择。但长文档要先 chunking,数字/否定语义要用其他方法补充。**

---

## 模块 4 · 向量检索:相似度算法 / ANN / ChromaDB

### 相似度算法(3 种主流)

#### ① 余弦相似度(Cosine Similarity)— 文本检索首选

公式:`cos(A, B) = A·B / (|A| × |B|)`

只关注方向,不关注绝对值。范围 -1 ~ 1,越大越相似。

**为什么适合文本**:文本长短不影响语义,余弦忽略长度。

#### ② 点积(Dot Product)

公式:`A·B = Σ(a_i × b_i)`

向量归一化后,点积 = 余弦相似度。**更快**(不除以模长)。

**实战**:OpenAI 推荐归一化后用点积替代余弦,加速 30%+。

#### ③ 欧氏距离(Euclidean Distance)

公式:`d = √Σ(a_i - b_i)²`

关注绝对距离。图像检索常用,**文本检索不用**。

### ANN(Approximate Nearest Neighbor)— 大规模必备

#### 问题:暴力搜索 O(n)

```
查询向量 q
对库里每个向量 v_i:
  计算余弦相似度(q, v_i)
排序,返回 Top-K
```

10 万文档 + 1024 维 = 1 亿次乘法,慢。

#### 解决:牺牲一点点精度换 100 倍速度

| 算法 | 原理 | 召回率 | 速度 | 用 |
|---|---|---|---|---|
| Brute Force | 全量扫描 | 100% | 慢 | < 1000 向量 |
| **HNSW**(Hierarchical Navigable Small World) | 图结构,层次化导航 | 95-99% | 快 | **ChromaDB/默认** |
| IVF(Inverted File Index) | K-means 聚类,只查最相关簇 | 90-95% | 很快 | 超大规模(亿级) |
| PQ(Product Quantization) | 向量压缩后再查 | 85-95% | 极快 | 极大规模 + 内存紧 |

**RCA 选 HNSW**:案例库 10-1000 条,HNSW 召回率够、速度够。

### ChromaDB 内部

**ChromaDB 是嵌入式向量库**(类似 SQLite,无需独立服务)。

**核心 API**:
```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")

collection = client.create_collection("incidents")

# 写入(自动 embedding 或外部 embedding)
collection.add(
    documents=["Pod 内存溢出导致 OOMKilled"],
    metadatas=[{"date": "2024-08-15", "service": "order-service"}],
    ids=["inc-001"]
)

# 查询
results = collection.query(
    query_texts=["内存不够被杀"],
    n_results=3
)
```

**关键设计**:
- 默认用 HNSW + 余弦相似度
- 支持 metadata 过滤(SQL-like:`where={"service": "order-service"}`)
- 支持外部 embedding(自己用 bge-m3 算好再塞进去)

### 检索质量评估

**召回率(Recall)** = 检索到的相关文档 / 所有相关文档。RCA 案例 10 条,召回率应 > 90%。

**精确率(Precision)** = 检索到的相关文档 / 检索到的总数。Top-3 里至少 2 条相关。

**实战调优**:
- Top-K 设大(10-20),再 LLM 筛(取最相关 3 条)
- 加 metadata 过滤(只查同期/同服务)

### 一句话总结

> **向量检索用余弦相似度(归一化后用点积加速),大规模用 HNSW 算法(95% 召回换 100 倍速度),ChromaDB 嵌入式 + 默认 HNSW 是 RCA 案例库首选。**

---

## 模块 5 · RAG 完整架构:Chunking / 检索 / 拼接 / Advanced

### 完整流程(7 步)

```
1. 加载(Load)       → 读文档:PDF / Markdown / HTML
2. 切分(Chunk)      → 拆成小块:500-1000 token / 块
3. 向量化(Embed)    → 每块算 1024 维向量
4. 存储(Store)      → 存入 ChromaDB
   ─── 以上是离线一次,以下是线上每次查询 ───
5. 检索(Retrieve)   → 用户问题向量化,查 Top-K 相似块
6. 拼接(Assemble)   → Top-K 块拼进 Prompt(模板)
7. 生成(Generate)   → LLM 基于拼接好的 Prompt 生成答案
```

### Chunking 策略(关键且常被忽略)

**为什么切分**:
- LLM context window 有限(64K/128K)
- 长文档整体 embedding 会丢失细节(向量被"平均")
- 检索粒度更准(只取相关片段,不取整篇)

#### 主流切分器

| 切分器 | 原理 | 适用 |
|---|---|---|
| **固定大小**(CharacterTextSplitter) | 每 N 字符切一刀,带 overlap | 简单文档 |
| **递归切分**(RecursiveCharacterTextSplitter) | 按 `\n\n` → `\n` → ` ` 优先级切 | **通用默认** |
| **按 Markdown 标题**(MarkdownHeaderTextSplitter) | 按 # / ## / ### 切 | 文档(如 RCA 案例) |
| **按语义**(SemanticChunker) | 用 embedding 检测语义边界切 | 长文 |
| **按代码结构**(CodeTextSplitter) | 按函数/类边界切 | 代码 |

#### 关键参数

```python
RecursiveCharacterTextSplitter(
    chunk_size=500,     # 每块 token 数(RCA 推荐 500-1000)
    chunk_overlap=50,   # 块间重叠(RCA 推荐 10-20%)
    separators=["\n\n", "\n", "。", " ", ""],  # 中文加"。"作为句子边界
)
```

**chunk_size 选择**:
- 太小(100 token):碎片化,上下文丢失
- 太大(5000 token):检索不准,context 浪费
- **RCA 推荐 500-1000 token**(每个案例约 1-2 块)

**chunk_overlap 选择**:10-20% 的 chunk_size,防止跨块信息丢失。

### RCA 应用:历史案例库

**数据准备**:10-30 条历史故障案例,每条格式:
```markdown
# 案例 #2024-0815:内存泄漏致 OOM

## 背景
order-service 频繁 OOMKilled,5 分钟内重启 12 次

## 现象
- Pod 内存从 200Mi 涨到 512Mi(limit)
- GC 日志: Full GC 每分钟 8 次
- 节点内存使用率 95%

## 根因
应用层 HashMap 缓存未设置上限,持续增长导致堆内存耗尽

## 处置
- 短期: limit 提到 1Gi
- 长期: 改用 Caffeine 缓存 + 最大容量限制
```

**切分**:每个案例整体作为一块(`chunk_size=1500`),不要切碎(案例要完整才能匹配)。

**检索**:用户告警 "Pod OOMKilled" → 检索到 Top-3 相似案例 → 拼进根因推断 Prompt。

### 拼接 Prompt 模板

```python
prompt = f"""
你是运维根因分析专家。

## 当前故障
{alert_description}

## 受影响资源
{affected_resources}

## 指标证据
{metrics_results}

## 日志证据
{logs_results}

## 历史相似案例(从知识库检索)
{retrieved_incidents}

## 任务
基于以上证据 + 相似案例,推断根因。

输出格式:
- 根因假设: ...
- 置信度: 0-100%
- 推理过程: ...
"""
```

### Advanced RAG 模式

#### ① Rerank(重排)

**问题**:向量检索 Top-10 召回率高但精确率低(很多相关但排序错)。

**解决**:Top-20 检索后,用 **cross-encoder**(如 bge-reranker)逐对精细打分,取 Top-5。

**对比**:
- Embedding(bi-encoder):快,但语义匹配粗
- Reranker(cross-encoder):慢,但精度高 2-3 倍

**RCA 加 reranker**:免费模型 bge-reranker-base,精度提升明显。

#### ② Hybrid Search(混合检索)

**机制**:向量检索(语义)+ 关键词检索(BM25)+ 加权融合。

**适合**:技术文档(指标名/PromQL 关键词需要精确匹配)。

```
查询: "query_prometheus P95 延迟"
向量检索 Top-5: 找语义相似的
BM25 检索 Top-5: 找含 "P95" "延迟" 关键词的
融合: Reciprocal Rank Fusion (RRF) → Top-5 最终
```

#### ③ HyDE(Hypothetical Document Embeddings)

**思路**:用户问题短 → 让 LLM 先生成假答案 → 用假答案检索 → 检索更准。

**例子**:
```
用户: "为什么内存泄漏"
LLM 生成假答案: "内存泄漏指..."
用假答案向量检索 → 找到真正的内存泄漏案例
```

**适合**:用户问题太短/太模糊的场景。RCA 不太需要(告警本身够具体)。

#### ④ Multi-Query Retriever

**思路**:LLM 把用户问题改写成 3-5 个不同角度的子问题,各自检索后合并。

**例子**:
```
原问题: "OOM 根因"
改写:
  - "Pod 内存溢出的常见原因"
  - "Java 内存泄漏排查方法"
  - "OOMKilled 故障案例"
各自检索 Top-3 → 合并去重 Top-5
```

### RAG 常见坑

| 症状 | 原因 | 解决 |
|---|---|---|
| 检索不到相关案例 | chunk 太大或 embedding 模型差 | 换 bge-m3 + chunk_size 调到 500-1000 |
| 检索到了但答错 | Prompt 拼接不当 / Top-K 太少 | Top-K 设 5-10,加 Rerank |
| LLM 编造案例 | 没在 Prompt 明确"只用检索到的" | System Prompt: "基于检索到的案例回答,不要编造" |
| 答非所问 | 检索 chunk 太碎,语义丢失 | 增大 chunk_size + overlap |
| Token 超限 | Top-K 太大,context 爆 | Top-K 限 5,每块限制长度 |

### 一句话总结

> **RAG = Load → Chunk(500-1000 token)→ Embed → Store → Retrieve(Top-5+Rerank)→ Assemble(Prompt 模板)→ Generate。Chunking 决定检索质量,Rerank/Hybrid/Multi-query 是进阶武器。**

---

## 速记卡

### 10 个必背数字

| 数字 | 含义 |
|---|---|
| Agent = LLM + **工具 + 循环** | Agent 三要素 |
| Function Calling 协议 **5 步** | 问 → tool_call → 执行 → response → 最终答 |
| tools JSON Schema **3 必填** | name / description / parameters |
| bge-m3 维度 **1024** | RCA 推荐的 embedding 维度 |
| OpenAI text-embedding-3-large 维度 **3072** | 最精细但贵 |
| chunk_size 推荐 **500-1000 token** | RCA 案例切分 |
| chunk_overlap 推荐 **10-20%** | 防跨块信息丢失 |
| **Top-K = 5** | 检索默认值,加 Rerank |
| HNSW 召回率 **95-99%** | 速度换精度的合理代价 |
| Reranker(cross-encoder)精度提升 **2-3 倍** | bge-reranker-base 免费 |

### 5 个口诀

1. **Agent = LLM 是大脑,工具是手脚,循环是生命**
2. **ReAct 边想边做,Plan-and-Execute 先规划后执行(LangGraph)**

3. **Function Calling:LLM 决策,你执行;description 决定智能程度**

4. **余弦看方向(文本),欧氏看距离(图像),归一化后用点积加速**

5. **RAG 七步走:Load → Chunk → Embed → Store → Retrieve → Assemble → Generate**

### 比赛理论题预测

1. **什么是 Agent?和普通 Chain 区别?**(LLM + 工具 + 循环;Chain 是预定义管道)
2. **ReAct 是什么?Thought/Action/Observation 循环?**(推理+行动闭环)
3. **Function Calling 完整流程?**(5 步:问 → tool_call → 执行 → response → 答案)
4. **Embedding 是什么?为什么能做语义搜索?**(文本→向量,相似文本靠近)
5. **余弦相似度 vs 欧氏距离,文本检索用哪个?**(余弦,忽略长度)
6. **什么是 HNSW?为什么用 ANN?**(图结构,牺牲 1-5% 召回换 100 倍速度)
7. **RAG 解决什么问题?**(幻觉 / 时效 / 私有数据)
8. **RAG 完整流程几步?**(7 步:Load/Chunk/Embed/Store/Retrieve/Assemble/Generate)
9. **chunk_size 怎么选?为什么不能太大太小?**(500-1000,太大检索不准/太小丢上下文)
10. **Reranker 是什么?和 Embedding 区别?**(cross-encoder 精排;bi-encoder 粗排)

### RCA Demo 直接落地的决策

| 决策 | 选 | 原因 |
|---|---|---|
| Agent 模式 | **Plan-and-Execute(LangGraph 8 节点状态图)** | 可控、可调试、可演示 |
| Function Calling 协议 | **OpenAI 标准 JSON Schema** | DeepSeek-V3 / 硅基流动都支持 |
| Embedding 模型 | **bge-m3(硅基流动免费)** | 中文好,1024 维够用 |
| 向量库 | **ChromaDB(嵌入式)** | 无需独立服务,零运维 |
| 检索算法 | **HNSW + 余弦相似度(ChromaDB 默认)** | 10-30 案例,默认够 |
| Chunking | **RecursiveCharacterTextSplitter, chunk_size=1000, overlap=100** | 案例文档大小适中 |
| Top-K | **5,后续加 bge-reranker-base** | 先跑通再加优化 |
| 拼接 Prompt | **结构化模板(背景+证据+案例+任务)** | 防幻觉 + 可解释 |
