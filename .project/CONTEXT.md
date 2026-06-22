# RCA Agent(运维根因分析智能体)

> 基于 LLM + LangGraph 的运维根因分析系统,覆盖 IaaS/PaaS/SaaS/容器,自动定位故障根因

## 项目性质

**Greenfield · 比赛参赛项目**

- 赛事:省内创新技能赛(个人赛)· AI 赛道
- 参赛者:6 年开发经验,0 AI 基础
- 时间:一周(工作日每天 1.5h + 周末 8h/天 ≈ 23.5h)
- 当前阶段:需求已确认,PRD 已产出,知识库已建立,代码尚未开始

## Build / Test / Lint

| Command | Action | 状态 |
|---------|--------|------|
| `pip install -r requirements.txt` | 安装 Python 依赖 | ❌ 待创建 |
| `python src/main.py` | 启动 FastAPI 服务 | ❌ 待创建 |
| `pytest tests/` | 运行测试 | ❌ 待创建 |
| `cd frontend && npm run dev` | 启动前端 | ❌ 待创建 |

> ⚠️ 代码尚未开始开发,以上为预期命令(Blueprint)

## Tech Stack

| 层 | 选型 | 置信度 |
|---|---|---|
| LLM | 硅基流动 DeepSeek-V3(云 API,免费额度) | ✅ 已确认 |
| Agent 编排 | LangGraph(状态机式) | ✅ 已确认 |
| 后端 | FastAPI(Python 3.11) | ✅ 已确认 |
| 前端 | React + Ant Design | ⚠️ 待定(Gradio 备选) |
| 向量库 | ChromaDB(嵌入式) | ✅ 已确认 |
| Embedding | bge-m3(硅基流动提供) | ✅ 已确认 |
| 数据源 | Prometheus + Loki + Alertmanager | ✅ 已有真实环境 |
| 根因粒度 | 资源级(Pod/Node/Service) | ✅ 已确认 |
| 拓扑来源 | 手写 YAML 静态拓扑 | ✅ 已确认 |

## Directory Map

```
rca-agent/
├── docs/
│   └── RCA-Agent-PRD.md          # 产品需求文档(完整,505行)
├── demo/
│   └── index.html                # HTML 交互演示(纯前端 Mock,482行)
├── knowledge/
│   ├── README.md                 # 知识库总览(待评审)
│   ├── README.xr.md              # Oracle 交叉评审结果
│   └── 001/                      # 学习材料(md + html)
│       ├── day0-ai-glossary.*    # AI术语表 + UnifiedModel详解
│       ├── day0-langchain-langgraph-overview.*  # 框架速览
│       └── reference-alibaba-rca.*  # 阿里RCA智能体参考
├── scripts/
│   └── convert_md_to_html.py     # Markdown→HTML 转换器
└── .project/                     # 需求追踪(zy-track)
```

## 核心架构(Blueprint)

```
告警触发/对话触发 → FastAPI 网关 → LangGraph RCA 工作流(8节点)
                                        ├─ 告警接收 → 告警聚合 → 拓扑关联
                                        ├─ 指标分析(PromQL) → 日志分析(LogQL)
                                        ├─ 历史案例检索(ChromaDB RAG)
                                        └─ 根因推断(LLM) → 报告生成
```

## 演示场景(3个)

1. **容器 OOM**:PodOOMKilled → 内存泄漏根因
2. **节点宕机**:NodeDown → 资源不足连锁故障
3. **慢查询超时**:对话触发 → 慢SQL致连接池耗尽

## Sub-files

- `pitfalls.md` — 已知陷阱(从真实错误中提取)
- `requirements/` — 活跃需求追踪
  - `001-ai-knowledge-sprint.md` — AI 知识 7 天速成
  - `002-rca-agent-mvp.md` — RCA 智能体 MVP 开发
- `archive/` — 已完成需求(含完整历史)

## 关键约束

- **时间极紧**:23.5h 总预算,必须聚焦
- **0 AI 基础**:学习曲线陡,概念必须简化
- **Oracle 评审已标记 6 个必修项**(理论权重/日历倒挂/无缓冲日等)
- **不做**:自愈(L4)/多Agent并行/摄像头场景/微调
