# 001 - AI 知识 7 天速成

## 版本

v1.0

## 创建时间

2025-06-22

## 完成时间

{done 时自动写入}

## 目标

7 天内掌握 RCA 智能体开发所需的 7 个 AI 核心概念,能独立编写 LangGraph 工作流 + Function Calling + RAG,为比赛理论考试和实操开发打基础。

## 范围外

- Transformer 数学推导 / 反向传播公式(不考深度,一句话理解即可)
- 模型训练 / 从零训练(用 API,不训练)
- Fine-tuning 实操(LoRA 只做理论了解,不实际跑)
- CNN / RNN / 计算机视觉(与 RCA 无关)
- Dify / Coze 等低代码平台(时间不够)

## 完成标准

- [ ] 能调用硅基流动 API 并获取结构化输出
- [ ] 能写出 Few-shot + CoT Prompt 让模型做根因分析
- [ ] 能用 Function Calling 让模型查询 Prometheus/Loki
- [ ] 能用 ChromaDB 做语义检索(存取+查询)
- [ ] 能用 LangGraph 编排 3+ 节点的工作流
- [ ] 能串联 RAG 完整链路(检索→拼接→生成)
- [ ] 能口述 30 个 AI 核心术语的含义(术语表自测通过)
- [ ] 能回答比赛理论高频题(每天 5 个 Q&A × 7 = 35 题全覆盖)

## 任务分解

> ⚠️ Oracle 评审已标记:需重排日历让难度与时间匹配

### Day 0(周日 6/22)— 环境搭建 + 预习
- [x] 注册硅基流动,获取 API Key
- [x] 浏览 Day0 速览文档(LangChain/LangGraph/术语表)
- [ ] 跑通第一段 LLM 调用代码(验证环境)
- [ ] `pip install langchain langchain-openai langgraph chromadb`

### Day 1(周一 6/23)1.5h — LLM API 调用 + 理论卡片
- [ ] 核心概念:LLM API / Token / Context Window / Temperature
- [ ] 理论卡片(15min):Transformer 一句话原理 / Pretrain→SFT→RLHF 三阶段
- [ ] 动手:跑通 `client.chat.completions.create()`
- [ ] Q&A 5 题 + 自测

### Day 2(周二 6/24)1.5h — Prompt + Few-shot
- [ ] 核心概念:System/User/Assistant / Few-shot / CoT
- [ ] 理论卡片:智能体设计原则(ReAct vs Plan-and-Execute)
- [ ] 动手:写告警分类 Prompt(Few-shot + JSON 输出)
- [ ] Q&A 5 题 + 自测

### Day 3(周三 6/25)1.5h — 结构化输出 + LangChain
- [ ] 核心概念:Pydantic / LangChain Chain / Output Parser
- [ ] 动手:用 LangChain 输出 RCAReport 对象
- [ ] Q&A 5 题 + 自测

### Day 4(周四 6/26)1.5h — Function Calling ⭐
- [ ] 核心概念:工具定义 / JSON Schema / tool_call 流程
- [ ] 理论卡片:大模型部署(vLLM/Ollama 一句话)
- [ ] 动手:定义 query_prometheus + query_loki 工具
- [ ] Q&A 5 题 + 自测
- [ ] ⚠️ Oracle 标记:难度最高但时间最少,如不够周末补

### Day 5(周五 6/27)1.5h — Embedding + 向量检索
- [ ] 核心概念:Embedding / 余弦相似度 / 向量库
- [ ] 动手:ChromaDB 存取 10 条历史故障
- [ ] Q&A 5 题 + 自测

### Day 6(周六 6/28)8h — LangGraph 状态机 ⭐⭐
- [ ] 核心概念:State / Node / Edge / Compile / 条件分支
- [ ] 动手:3+ 节点工作流(receive→analyze→infer)
- [ ] 进阶:条件路由(指标够不够→出报告/再查)
- [ ] Q&A 5 题 + 自测

### Day 7(周日 6/29)8h — RAG 串联 + 排练
- [ ] 核心概念:RAG 完整流程 / Chunking 策略
- [ ] 动手:串联 Day4(FC) + Day5(检索) + Day6(Graph)
- [ ] 最小 RCA:输入告警→检索案例→推断根因→输出报告
- [ ] 下午:理论总复习 + 术语自测 + 比赛排练
- [ ] Q&A 5 题 + 自测

## 关键决策

| 决策 | 选择 | 原因 | 变更前 |
|------|------|------|--------|
| 时间投入: 工作日时长 | 1.5h/天 | 用户工作日可用时间有限 | — |
| LLM 平台: 服务商 | 硅基流动(DeepSeek-V3) | 免费额度,中文好,FC完善 | — |
| 理论深度: Transformer/微调 | 砍掉,仅一句话卡片 | 时间不够,优先实操 | — |
| 学习形式: 问答驱动 | 每天5个Q&A + 可跑代码 | 模拟比赛理论题,一举两得 | — |
| 日历: Day4 FC 位置 | ⚠️ 待重排(Oracle建议挪周末) | 难度最高但只有1.5h | — |

## 进度记录

### 2025-06-22

- **完成**: 知识库建立(术语表 + LangChain/LangGraph速览 + 阿里RCA参考),文档转HTML,Day0预习材料就绪
- **阻塞**: 日历未最终确认(Day4 FC 时间不足问题待解决)
- **下一步**: 今晚跑通环境,确认 Day1 正式开始
