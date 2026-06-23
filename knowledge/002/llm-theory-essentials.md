# 大模型理论必备速览

## 模块 1 · Transformer 与 Attention 工作原理

### 核心概念

**Transformer 是几乎所有现代大模型(GPT/DeepSeek/Llama/Qwen)的底层神经网络架构**,2017 年 Google 论文《Attention Is All You Need》提出。

它解决的核心问题:**如何让模型处理一段文本时,理解词与词之间的关系**(而不是逐字顺序处理)。

### Self-Attention 机制(最关键)

处理每个词时,模型同时"看到"句子里**所有其他词**,并算出一个**注意力权重**——决定该关注谁、忽略谁。

**例子**:句子"苹果发布了新手机"
- 处理"苹果"时,attention 关注"发布""手机"→ 判断是公司(不是水果)
- 处理"发布"时,attention 关注"苹果""手机"→ 理解动作的主体和客体

**类比**:SQL 的 JOIN——根据关联性把分散的信息拼起来。但 Transformer 是**全表自连接**(每个词 JOIN 所有词),用注意力权重替代 ON 条件。

### Multi-Head Attention

一组 attention 只能学一种关系。Multi-Head = **多组 attention 并行**,每组学不同维度:
- 有的 head 关注语法(主谓宾)
- 有的 head 关注语义(实体关系)
- 有的 head 关注位置(相邻词)

GPT-3 用 96 个 head,DeepSeek-V3 大约 128 个。

### Positional Encoding(位置编码)

Attention 机制本身**不知道词的顺序**(它把句子当无序集合)。所以需要额外给每个位置加一个**位置编码**(类似数组的 index,但是用数学函数生成,让模型能学到"相邻""远距"等概念)。

**类比**:数据库行号——SQL 不关心行顺序,但你想按顺序读时需要 ORDER BY 一个位置字段。

### Feed-Forward Network(FFN)

每个位置经过 attention 后,再过一个两层全连接网络(MLP)做特征变换。这一步是**逐位置独立**的(每个 token 自己过 FFN,不跨位置)。

**类比**:attention 是横向 JOIN(找关系),FFN 是纵向处理(每个 token 自己做特征提取)。

### 关键数字

- **GPT-3(2020)**: 175B 参数, 96 层, 96 head, 上下文 2K
- **DeepSeek-V4-Pro(2026.4)**: 1.6T 参数(MoE,激活 49B), 上下文 1M;V4-Flash(284B/13B 激活)为高效版。V3(2024, 671B/37B)已退居上一代
- **7B 模型**: 通常 32 层, 32 head, 隐藏维度 4096

### 一句话总结

> **Transformer = Self-Attention(让每个词看到所有词) + FFN(每个词自己深化)+ 残差连接(防梯度消失)。它取代了 RNN 的"逐字处理",让模型能并行计算 + 全局建模。**

---

## 模块 2 · 训练三阶段:Pretrain → SFT → RLHF

### 总览

| 阶段 | 数据 | 数据量 | 产出 | 成本 |
|---|---|---|---|---|
| Pretrain | 无标注网页/书籍/代码 | 万亿 token | Base Model(会续写,不会对话) | 千万美级别 |
| SFT | 人工问答对 | 万-百万对 | Chat Model(能对话,但答得糙) | 千美元级 |
| RLHF | 人工偏好排序 | 万-十万条 | 对齐后的最终模型 | 万美元级 |

### 阶段 1:Pretrain(预训练)

**做什么**:让模型玩"猜下一个词"游戏。喂一段文本,遮住最后一个词,让模型猜。

**示例训练数据**:
```
输入: "中国的首都是"
标签: "北"  ← 模型要预测这个
输入: "北京的"
标签: "京"
```

**数据来源**:
- Common Crawl(网页爬虫,万亿级)
- Wikipedia(百科,百亿级)
- GitHub(代码,千亿级)
- 书籍 / 论文 / 对话数据

**产出**: Base Model(基座模型)。**只会续写,不会回答问题**。比如问它"什么是 RCA",它可能续写成"什么是 RCA?什么是 RBAC?什么是..."而不是给你答案。

**类比**: Pretrain 像通识教育——学了语文数学历史,但不会做具体工作。

### 阶段 2:SFT(Supervised Fine-Tuning · 指令微调)

**做什么**:用"问-答"标注数据教模型**听指令**。

**训练数据格式**:
```json
{
  "instruction": "解释什么是根因分析",
  "input": "",
  "output": "根因分析(RCA)是定位故障根本原因的方法..."
}
```

**关键技巧**:只在 `output` 部分算 loss,**不惩罚模型在 `instruction` 上的预测**(因为指令是用户给的,不是模型该生成的)。

**产出**: Chat Model / Instruct Model(如 DeepSeek-V3)。这时模型能正常对话了,但可能答得不够好(太啰嗦、有偏见、不安全)。

**类比**: SFT 像职业培训——学会了具体岗位技能(回答问题、写代码、翻译)。

### 阶段 3:RLHF(Reinforcement Learning from Human Feedback · 人类反馈强化学习)

**做什么**:让模型回答**更讨人喜欢**——安全、有用、礼貌。

**完整流程(4 步)**:

1. **采样**: 用 SFT 模型对同一个 prompt 生成多个不同回答(用 Temperature=1)
2. **人工标注**: 让标注员对回答排序(回答 A > B > C)
3. **训练奖励模型(Reward Model)**: 用偏好数据训练一个"打分器",能自动给回答打分
4. **PPO 强化学习**: 用打分器作为奖励信号,优化 SFT 模型让它生成高分回答

**DPO(Direct Preference Optimization)** 是 2023 年的简化方案,**跳过训练 Reward Model**,直接从偏好数据优化模型。现在越来越多模型用 DPO 替代 RLHF。

**产出**: 最终发布版模型(如 DeepSeek-V3-Chat)。

**类比**: RLHF 像 KPI 考核——根据反馈调整行为,让回答"讨喜"。

### 三个阶段的边界

| 问题 | 谁负责 |
|---|---|
| 模型能生成通顺中文 | Pretrain |
| 模型能听懂"翻译这句话" | SFT |
| 模型拒绝"教我做炸弹" | RLHF |
| 模型回答更详细、不啰嗦 | RLHF |
| 模型知道"RCA 是什么意思" | Pretrain(从文档学到) |

### 一句话总结

> **Pretrain 教模型"说话"(语言能力),SFT 教模型"听话"(指令遵循),RLHF 教模型"讨喜"(价值对齐)。**

### 必背口诀(比赛高频题)

> **Pretrain:海量无标注,学语言规律,产 Base Model**
> **SFT:指令问答对,教怎么答,产 Chat Model**
> **RLHF:偏好排序,教答得好,产 Aligned Model**

---

## 模块 3 · 采样参数全解:Temperature / Top-p / Top-k / Penalty

### 背景:LLM 输出的本质

模型每次生成一个 token,会先算出**词表所有 token 的概率分布** P(token | context)。比如:

```
上下文: "中国的首都"
P("北") = 0.85
P("南") = 0.05
P("上") = 0.04
P("广") = 0.02
... 剩下 5 万 token 共享 0.04
```

**采样参数控制如何从这个分布中挑 token**。

### Temperature(温度)

**公式**: P'(token) ∝ P(token) ^ (1 / T)

简单理解:把概率分布"压平"或"拉陡"。

| T 值 | 效果 | 用途 |
|---|---|---|
| T = 0 | 完全贪婪,永远选最高概率 | 代码生成、JSON 输出、RCA、数学 |
| T = 0.3 | 几乎确定,极小随机 | 翻译、摘要 |
| T = 0.7 | 平衡(OpenAI 默认) | 通用对话、问答 |
| T = 1.0 | 原始分布不变 | 创意写作 |
| T = 1.5+ | 分布很平,长尾 token 也可能选中 | 头脑风暴 |

**RCA 必用 T=0**:同一个告警,今天说根因是 A,明天说根因是 B,这是灾难。

### Top-p(Nucleus Sampling · 核采样)

**做什么**: 只从"概率累计前 p%"的 token 里选,长尾全部丢弃。

**例子**(上下文 "中国的首都"):
- p = 0.9:候选 ["北", "南", "上"] 共占 94% 概率,只从这 3 个里选
- p = 0.5:候选 ["北"] 占 85%,只从 1 个里选(等于贪婪)

**默认值**: p = 1(不限制,等价于关闭)

**实战**:通常 **Temperature + Top-p 一起调**,比如 T=0.7 + p=0.9。不要只调一个。

### Top-k

**做什么**: 只从概率最高的 **k 个** token 里选,不管它们累计概率多少。

**例子**:
- k = 5:候选 = Top 5 token
- k = 50:候选 = Top 50 token

**vs Top-p**: Top-k 是**固定数量**,Top-p 是**固定概率累计**。Top-p 更自适应(高置信时少选,低置信时多选),所以**现代模型默认用 Top-p**。

### Frequency Penalty / Presence Penalty

**做什么**: 惩罚**已经出现过的 token**,防止重复。

| 参数 | 惩罚方式 | 范围 |
|---|---|---|
| Frequency Penalty | 出现次数越多惩罚越重 | -2 ~ 2 |
| Presence Penalty | 只要出现过就惩罚 | -2 ~ 2 |

**实战**:
- 长文生成(怕啰嗦):0.5 ~ 1.0
- 代码生成(怕改词):0
- 翻译/摘要:0.3

### 默认参数对照(主流 API)

| 场景 | Temperature | Top-p | Penalty |
|---|---|---|---|
| OpenAI gpt-4 默认 | 1.0 | 1.0 | 0 |
| DeepSeek 推荐(代码) | 0 | - | - |
| DeepSeek 推荐(对话) | 0.7 | 0.95 | 0 |
| Claude 默认 | 1.0 | - | - |
| **RCA 推荐** | **0** | **1** | **0** |

### 一句话总结

> **Temperature 控制分布陡峭(确定性 vs 创造性),Top-p 过滤长尾,Penalty 防重复。RCA 永远 T=0 + p=1 + 无 penalty,要确定性。**

---

## 模块 4 · 推理优化:KV Cache / 量化 / 部署方式

### 背景:为什么需要优化

7B 模型推理 1 个 token,理论上需要 N×N 矩阵乘法(N = 隐藏维度 4096)。
- 每生成 1 个 token ≈ 14 亿次浮点运算(7B 模型)
- 生成 1000 token ≈ 1.4 万亿次运算
- 没 GPU 跑不动,有 GPU 也要优化才能商业化

### KV Cache(关键优化 · 必考)

**问题**: 生成第 N 个 token 时,attention 需要前面 N-1 个 token 的 **Key** 和 **Value** 向量。如果每步都重算,计算量是 O(N²)。

**解决**: 把前面 token 的 K/V 缓存下来,下一步直接复用。

**类比**: 像数据库的 materialized view——把中间结果预先算好存起来,下次查询直接用。

**显存代价**(7B 模型,FP16):
- 每个 token 的 KV Cache ≈ 1 MB
- 4096 token 上下文 ≈ **4 GB** 显存(比模型本身还大!)
- 128K 上下文 ≈ 128 GB(根本塞不下普通 GPU)

**优化方案**:
- **PagedAttention(vLLM)**:像 OS 的虚拟内存,把 KV Cache 分页管理,显存利用率从 30% 提到 90%+
- **Sliding Window Attention**:只看最近 N 个 token,牺牲一点精度换显存
- **GQA(Grouped Query Attention)**:多个 query head 共享 K/V,减少 KV Cache 大小

### 量化(Quantization)

**做什么**: 把模型参数从高精度(FP16)压到低精度(INT8 / INT4),牺牲一点精度换巨大显存节省。

| 精度 | 7B 模型显存 | 速度 | 精度损失 |
|---|---|---|---|
| FP32 | 28 GB | 慢 | 基准 |
| FP16 / BF16 | 14 GB | 标准 | <0.5% |
| INT8 | 7 GB | 快 | 0.5-1% |
| INT4 | 4 GB | 最快 | 2-5% |

**主流量化方案**:
- **GPTQ**: 后训练量化,需要校准数据
- **AWQ**: 激活感知量化,精度更好
- **GGUF**: llama.cpp 用的格式,CPU/GPU 都能跑

**实战**: 7B 模型 INT4 量化后,Apple M1 16GB MacBook 都能跑(对开发机友好)。

### Batching

**做什么**: 多个请求合并成一个 batch 一起算,GPU 并行度高 10-100 倍。

**Continuous Batching(vLLM/ORCA 算法)**:
- 旧 batching 要等一个 batch 全部完成才接新请求,慢
- Continuous Batching:每个 token step 都能动态加入新请求 / 移除完成请求
- 吞吐量比朴素 batching 高 10-30 倍

### 部署方式对比

| 方式 | 优点 | 缺点 | 适用 |
|---|---|---|---|
| **云 API**(硅基流动/DeepSeek/OpenAI) | 零部署,按量计费 | 数据出域,长期贵 | 原型/学习/RCA Demo |
| **vLLM 自部署** | 吞吐量高,数据私有 | 要 GPU 机器 | 生产/批量 |
| **Ollama** | 一行命令起服务 | 性能比 vLLM 差 | 本地开发 |
| **llama.cpp + GGUF** | CPU 也能跑 | 速度慢 | 个人研究 |

### 一句话总结

> **KV Cache 是推理加速的第一功臣,PagedAttention 让它显存高效;量化让 7B 模型塞进笔记本;vLLM 是生产部署首选。**

### 关键数字记忆

- 7B FP16 = 14 GB(基线)
- 7B INT4 = 4 GB(笔记本可跑)
- vLLM vs HF Transformers: 吞吐量差 **20-30 倍**
- KV Cache 每 1K token ≈ 1 GB(7B FP16)

---

## 模块 5 · LLM 工程常识:计费 / 流式 / 限流 / 幻觉

### 计费模型

**所有 LLM API 按 token 计费**,**input 和 output 分开算**(output 通常贵 2-3 倍)。

| 模型 | Input 价格 | Output 价格 |
|---|---|---|
| GPT-5.5(2026.4) | $5 / 1M token | $30 / 1M |
| Claude Sonnet 4.6(2026.2) | $3 / 1M | $15 / 1M |
| **DeepSeek-V4-Pro(硅基流动)** | **¥3 / 1M** | **¥6 / 1M** |
| DeepSeek-V4-Flash(硅基流动) | ¥1 / 1M | ¥2 / 1M |

**对比**: DeepSeek-V4-Flash 比 GPT-5.5 便宜 **30-100 倍**(输入约 36×,输出约 107×);V4-Pro 便宜 10-30 倍。中文强,Demo 选 V4-Flash 最划算。

**成本估算(RCA 项目全程)**:
- 学习 Day 1-7: 约 100 万 token(每天 15 万)≈ ¥1
- RCA Demo 开发调试: 约 500 万 token ≈ ¥5
- 比赛演示 3 场: 约 50 万 token ≈ ¥0.5
- **总计**: ¥10 以内(硅基流动免费额度足够)

### 延迟特性

| 指标 | 典型值 | 影响 |
|---|---|---|
| 首 token 延迟(TTFT) | 0.3 - 2 秒 | 用户感知"开始回答"的速度 |
| 后续 token 速率 | 30 - 100 token/秒 | 长文生成的总时长 |
| Prompt 处理延迟 | 与 token 数线性相关 | 10K token prompt 处理就要 1-3 秒 |
| 上下文越长 | 速度越慢 | 128K 上下文比 4K 慢 3-5 倍 |

**实战**: RCA 报告生成(输入 5000 token 证据 + 输出 1000 token 报告)总时长约 15-30 秒。Web UI 必须用流式输出,否则用户体验糟糕。

### 流式输出

**协议**: SSE(Server-Sent Events),基于 HTTP 长连接。

**调用**:`stream=True`,API 返回 generator,每次 yield 一个 token chunk。

**为什么必须用**:
- UX:用户看到字一个一个出来,感觉"模型在思考",而不是干等 30 秒
- 错误恢复:中途出错能部分返回,不全丢
- 长输出不超时:HTTP 超时通常 60s,非流式生成 2000+ token 容易超

### 限流(Rate Limiting)

**维度**:
- **RPM** (Requests Per Minute): 每分钟请求数,如 60
- **TPM** (Tokens Per Minute): 每分钟 token 数,如 100K
- **并发数**: 同时进行的请求数,如 10

**超限响应**: HTTP 429 + `Retry-After` header

**应对策略**:
- 指数退避重试:1s → 2s → 4s → 8s
- 多账号轮询(灰色但常用)
- 本地降级:切到 Ollama 跑本地模型

### 非确定性(必懂)

**问题**: **即使 Temperature = 0,同一 prompt 多次调用结果也可能不同**。

**原因**:
1. GPU 并行浮点运算非结合性:`(a+b)+c ≠ a+(b+c)`,不同批次计算顺序不同
2. 框架内部优化(如 CUDA kernel autotuning)导致非确定性
3. 服务端 batching 策略变化影响数值

**实战**:
- 写自动化测试时**不要断言严格相等**,而是用相似度阈值
- 想要**真复现**,需要固定 seed + 同一硬件 + 同一框架版本(很难)

### 幻觉(Hallucination)成因

**LLM 一本正经胡说八道** 的根源:

| 成因 | 解释 |
|---|---|
| 概率采样本质 | 模型选的是"最可能"的 token,不是"正确"的 token |
| 训练数据噪声 | 互联网数据本身就充满错误 |
| 知识时效 | 训练截止后的事实,模型不知道(如新总统名字) |
| 缺乏事实核查 | Transformer 没有"我不知道"的机制,倾向编造 |
| Prompt 模糊 | 用户没给清楚约束,模型自由发挥 |

**应对(RCA 必用)**:
- **RAG**: 让模型基于检索到的真实文档回答,而不是凭记忆
- **Function Calling**: 让模型查 Prometheus/日志,不编造数据
- **System Prompt 约束**: "如果不知道就回答'信息不足',不要编造"
- **Temperature = 0**: 至少保证确定性,便于调试

### 一句话总结

> **LLM 工程化 = 算 token 成本 + 用流式输出避超时 + 限流退避 + 假设输出非确定 + 用 RAG/FC 防幻觉。RCA Demo 这 5 点必须都考虑到。**

---

## 速记卡(地铁快到站时扫一眼)

### 10 个必背数字

| 数字 | 含义 |
|---|---|
| 1 汉字 ≈ **1.5-2** token | Token 计费常识 |
| DeepSeek-V3 上下文 **128K** | 一次能塞 6 万汉字 |
| 7B FP16 = **14 GB** | 显存基线 |
| 7B INT4 = **4 GB** | 笔记本能跑 |
| DeepSeek-V4-Flash 比 GPT-5.5 便宜 **30-100 倍** | 学习/Demo 选它 |
| GPT-3 **175B** 参数 / 96 层 | 历史标杆 |
| Temperature = **0** | RCA 必用 |
| KV Cache 每 1K token ≈ **1 GB** | 推理显存大头 |
| vLLM 比 HF Transformers 快 **20-30 倍** | 生产部署首选 |
| Output 比 Input 贵 **2-3 倍** | 短 prompt 长 output 的成本陷阱 |

### 5 个口诀

1. **Pretrain 教说话,SFT 教听话,RLHF 教讨喜**
2. **Attention 让每个词看到所有词,FFN 让每个词深化自己**
3. **Temperature 控制分布陡峭,Top-p 过滤长尾,Penalty 防重复**
4. **KV Cache 是推理加速第一功臣,PagedAttention 让它不爆显存**
5. **RCA 工程:算成本 / 用流式 / 防限流 / 假设非确定 / RAG 防幻觉**

### 比赛理论题预测

1. **Transformer 的核心机制是什么?**(Self-Attention,让每个位置看到所有位置)
2. **大模型训练的三个阶段?**(Pretrain / SFT / RLHF)
3. **Temperature 的作用?RCA 用多少?**(控制随机性,0)
4. **什么是 KV Cache?为什么重要?**(缓存历史 K/V,推理加速)
5. **量化的作用?INT4 vs FP16?**(压缩显存,4GB vs 14GB)
6. **什么是幻觉?如何应对?**(编造事实,RAG + FC + System Prompt)
7. **LLM API 和 REST API 的区别?**(非确定 / 流式 / 按 token 计费)
8. **Function Calling 本质是什么?**(模型决定调哪个函数,不是自己执行)
9. **RAG 解决什么问题?**(幻觉 / 时效 / 私有数据)
10. **Top-p 和 Top-k 区别?**(概率累计 vs 固定数量)

---

## 配套学习路径

| 读完本文后 | 做什么 |
|---|---|
| 今晚(6/22 周日)| 跑通 `day0-langchain-langgraph-overview.md` Part 4 最小测试 |
| 明早地铁 | **本文重读 + glossary 30 术语巩固** |
| 明晚(6/23 周一)| Day 1 动手实验(代码部分) |
| 周二(6/24)| 生成 `knowledge/002/day2-prompt-theory.md`(等下一轮要求) |

---

> **读完本文,你应该能回答**:Transformer 是什么 / 大模型怎么训练出来的 / 为什么 Temperature=0 / 为什么需要 KV Cache / 量化为什么必要 / LLM 为什么会幻觉。
>
> **不能回答的(留给后续)**:怎么写 Prompt(Few-shot/CoT)/ 怎么用 Function Calling / 怎么搭 LangGraph 工作流 / 怎么做 RAG。这些等动手日学。
