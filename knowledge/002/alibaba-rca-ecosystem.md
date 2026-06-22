# 阿里 RCA 生态深度借鉴

## 概览

阿里在 RCA 智能体方向有 3 个值得关注的开源项目,本文基于实际仓库代码(非营销话术)分析各自的核心设计与可借鉴点。

| 项目 | 仓库 | 角色 | 对你的价值 |
|---|---|---|---|
| **UnifiedModel(UModel)** | alibaba/UnifiedModel | 语义层 / 对象图 | topological.yaml 建模思路 + Runbook 诊断协议 |
| **sysom_mcp** | alibaba/sysom_mcp | MCP 工具封装范式 | PromQL/LogQL 工具的工程化封装套路 |
| **AgentScope 2.0** | agentscope-ai/agentscope | 全栈 Agent 平台 | 工具系统/权限/工作区设计参考 |

**关键认知**:UModel **不是 RCA 算法**,而是给 LLM 提供上下文的**语义层**;真正的根因推理发生在 LLM 端的 Skill prompt 里。这一定位决定了它的设计取舍。

---

## 模块 1 · UnifiedModel(UModel)— 语义层 / 对象图

### 1.1 仓库元信息(已验证)

- **URL**: https://github.com/alibaba/UnifiedModel
- **Stars**: 183 · **语言**: Go · **License**: NOASSERTION(自定义)
- **创建**: 2026-05-06 · **最近提交**: 2026-06-22
- **Topics**: `ai-agent`, `aiops`, `cmdb`, `knowledge-graph`, `mcp`, `object-graph`, `observability`, `semantic-layer`

### 1.2 真实架构 — 22 个 model kinds

仓库的 `schemas/manifest.yaml` 注册了 **22 个 model kinds**(不是 3 类节点):

```
Datasets (9 种):
  entity_set          ← 实体(服务/Pod/Node)
  entity_source       ← 实体数据源(CMDB 同步)
  metric_set          ← 指标(Prometheus)
  log_set             ← 日志(Loki/ES)
  trace_set           ← 链路(OpenTelemetry)
  event_set           ← 事件(告警/K8s Event)
  profile_set         ← 持续性能分析(eBPF)
  runbook_set         ← 诊断手册
  explorer            ← 仪表盘(Grafana)

Storages (7 种):
  prometheus, aliyun_prometheus, elasticsearch
  mysql, sls_logstore, sls_metricstore, sls_entitystore
  external_storage

Links (6 种):
  entity_set_link     ← EntitySet ↔ EntitySet(拓扑关系)
  entity_source_link  ← EntitySource → EntitySet(数据同步)
  data_link           ← EntitySet ↔ DataSet(数据归属)
  storage_link        ← DataSet ↔ Storage(物理存储)
  runbook_link        ← EntitySet ↔ RunbookSet(诊断绑定)
  explorer_link       ← DataSet ↔ Explorer(可视化绑定)
```

**开发者类比**:类似一个**带语义的 ORM**——每个实体类型有 schema,实体间有关系,数据绑到具体存储。LLM 通过 SPL(UModel Query Language)查询这个对象图。

### 1.3 EntitySet 实际 YAML(incident-investigation 示例)

```yaml
kind: entity_set
schema: { url: "umodel.aliyun.com", version: "v0.1.0" }
metadata:
  name: "platform.service"
  domain: platform
  display_name: { en_us: "Service", zh_cn: "服务" }
spec:
  fields:
    - { name: id, type: string }
    - { name: status, type: string }
    - { name: sla_tier, type: string }
    - { name: qps, type: string }
    - { name: latency_p99_ms, type: string }
    # 17 个字段
  primary_key_fields: [id]
  id_generator: "id"
  name_fields: [display_name]
```

### 1.4 MetricSet 内嵌 PromQL 生成器(关键设计)

MetricSet 不是被动数据容器,而是**预生成 PromQL**:

```yaml
kind: metric_set
metadata: { name: "platform.service.metrics", domain: platform }
spec:
  metrics:
    - name: latency_p99_ms
      unit: ms
      type: gauge
      generator: 'histogram_quantile(0.99, sum(rate(platform_service_request_duration_seconds_bucket{service_id="$service_id"}[1m])) by (le)) * 1000'
      golden_metric: true
    - name: client_retry_rate
      generator: 'sum(rate(platform_service_client_retry_total{service_id="$service_id"}[1m])) / sum(rate(platform_service_client_request_total{service_id="$service_id"}[1m]))'
      golden_metric: true
```

**借鉴点**:`$service_id` 这种 token 化 PromQL 让 LLM **不用写 PromQL**,只填实体 ID——大幅降低幻觉风险。RCA Demo 可以在 topology.yaml 里给每个服务预定义 golden metrics。

### 1.5 Runbook 6 类(2 已弃用)

`schemas/core/dataset/runbook_set.schema.yaml` 定义 6 个字段:

| 字段 | 类型 ref | 状态 |
|---|---|---|
| `observations` | observation:v1 | **experimental**(主用) |
| `actions` | action_config:v1 | **deprecated** |
| `toolkits` | toolkit:v1 | **experimental**(主用) |
| `knowledge` | knowledge_config:v1 | **deprecated** |
| `automations` | automation_config:v1 | **experimental** |
| `skills` | skill_config:v1 | **experimental**(主用) |

**实际有效的 4 类**:observations / toolkits / automations / skills。

### 1.6 Runbook 实际 YAML(platform.service.ops.yaml,445 行)

**Observation(观察)— 用 SPL 查询对象图**:

```yaml
observations:
  - name: upstream_retry_amplification
    phenomenon:
      phenomenon_type: query
      inputs:
        - { name: service_id, type: string, required: true }
      outputs:
        - { name: upstream_services, type: json }
      properties:
        step1_query: '.topo | graph-call getDirectRelations([(:\"platform@platform.service\" {__entity_id__: \"${service_id}\"})]) | with(__relation_type__=''calls'')'
    conclusions:
      - condition: "any(config_changes, change_detail contains 'retry')"
        severity: error
        properties:
          next_action: "rollback_config_change"
```

**Toolkit(工具)— 带风险分级**:

```yaml
toolkits:
  - name: config_management
    toolkit_type: api_call
    tools:
      - name: rollback_config_change
        input_schema:
          properties:
            config_change_id: { type: string }
          required: [config_change_id]
        risk_level: medium
        idempotent: true
        confirmation_required: true     # ← Human-in-the-loop
```

**Skill(Agent Skill)— 内嵌完整 prompt**:

```yaml
skills:
  - name: incident-investigation
    priority: 1
    allowed_tools: "rollback_config_change apply_rate_limit scale_workload"
    files:
      - name: SKILL.md
        content: |
          # Incident Investigation Skill
          You are an SRE investigation agent. Use UModel's query surfaces
          (.entity, .topo, .umodel) to systematically investigate...
          ## Investigation Protocol
          ### Phase 1: Identify ...
          ### Phase 2: Observe (execute observations in order) ...
          ### Phase 3: Correlate ...
          ### Phase 4: Recommend ...
```

### 1.7 incident-investigation Demo 已验证

`examples/incident-investigation/deploy/start.sh` 一键拉起 UModel + Prometheus + ES + 数据生成器:

```bash
# 场景
{
  "scenario": {
    "title": "Payment Gateway P99 Latency SLO Breach",
    "root_cause": "Upstream retry amplification (2→5 retries) × promotion traffic (3.5x) = 8.75x effective load",
    "red_herring": "payment-gw v3.2.1 deployment 12h ago (trivial logging change)",
    "resolution": "Rollback cfg-checkout-retry via runbook tool rollback_config_change"
  },
  "counts": { "entities": 95, "relations": 126 }
}
```

**亮点**:Red Herring(误导项)——v3.2.1 部署是干扰,真正根因是上游重试配置。这测 Agent 的**证伪能力**,不只是模式匹配。

### 1.8 MCP 集成

`cmd/umodel-mcp/` 实现 MCP server:
- 协议版本 `2025-06-18`
- 3 种传输:stdio / Streamable HTTP / legacy SSE
- 暴露:`tools/list` / `tools/call` / `resources/read` / `prompts/get`
- 双编码:`content[].text`(TOON 格式)+ `structuredContent`(JSON)

### 1.9 借鉴清单(对你 RCA Demo 的实际价值)

| 借鉴点 | 实施难度 | 价值 |
|---|---|---|
| **YAML 化 topology**——给每个服务定义 metrics/log/depends_on | 低 | ⭐⭐⭐⭐⭐ |
| **预生成 PromQL**——把 query 写死在 YAML 里,LLM 只填 ID | 低 | ⭐⭐⭐⭐⭐ |
| **Observation 模式**——每个故障类型预定义"该查什么指标" | 中 | ⭐⭐⭐⭐ |
| **Toolkit 风险分级**——`risk_level` + `confirmation_required` | 中 | ⭐⭐⭐ |
| **Skill 内嵌完整 prompt**——把 RCA 协议写成 SKILL.md | 低 | ⭐⭐⭐⭐ |
| **Red Herring 测试集**——故意放干扰项测证伪能力 | 中 | ⭐⭐⭐ |
| **整套 UModel 部署**——Go 服务 + Docker compose | ❌ 太重 | 不做 |

---

## 模块 2 · sysom_mcp — MCP 工具封装范式

### 2.1 仓库元信息(已验证)

- **URL**: https://github.com/alibaba/sysom_mcp
- **Stars**: 70 · **语言**: Python · **License**: README 称 Apache 2.0(GitHub 显示 NOASSERTION)
- **创建**: 2025-12-05 · **最近提交**: 2026-03-24
- **依赖**:`fastmcp==2.13.1` + `mcp==1.22.0`(SDK 协议 2025-06-18)

### 2.2 真实工具列表(21 个,已验证)

| # | 工具名 | 模块 | 分类 |
|---|---|---|---|
| 1-2 | `initial_sysom`, `check_sysom_initialed` | initial_sysom_mcp.py | Onboarding |
| 3-6 | `list_all_instances`, `list_pods_of_instance`, `list_clusters`, `list_instances` | am_mcp.py | App Management |
| 7 | `memgraph` | mem_diag_mcp.py | **Memory 分析** |
| 8 | `javamem` | mem_diag_mcp.py | **JVM 内存** |
| 9 | `oomcheck` | mem_diag_mcp.py | **OOM 诊断** |
| 10 | `iofsstat` | io_diag_mcp.py | **IO 文件系统** |
| 11 | `iodiagnose` | io_diag_mcp.py | **IO 诊断** |
| 12 | `packetdrop` | net_diag_mcp.py | **网络丢包** |
| 13 | `netjitter` | net_diag_mcp.py | **网络抖动** |
| 14-15 | `delay`, `loadtask` | sched_diag_mcp.py | 调度器 |
| 16-19 | `create_vmcore_diagnosis_task`, `create_dmesg_diagnosis_task`, `query_diagnosis_task`, `list_history_tasks` | crash_agent_mcp.py | **Crash/Vmcore** |
| 20-21 | `vmcore`, `diskanalysis` | other_diag_mcp.py | Vmcore/磁盘 |

> **注**:`metrics_mcp.py` 整个文件**被注释掉了**,提供 0 个工具——README 列了但实际不工作。

### 2.3 工具定义 5 层模式(verbatim 代码)

每个工具严格遵循这个结构:

```python
# ── Layer 1: Pydantic Params Model(内部 API 契约)──
class OOMCheckDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    instance: Optional[str] = Field(None, description="实例ID")
    pod: Optional[str] = Field(None, description="Pod名称")
    namespace: Optional[str] = Field(None, description="Pod命名空间")
    # ...

# ── Layer 2: @mcp.tool 装饰器(带 tags 分组)──
@mcp.tool(tags={"sysom_memdiag"})

# ── Layer 3: async 函数 + Pydantic Field(自动生成 JSON Schema)──
async def oomcheck(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: Optional[str] = Field(None, description="实例ID"),
    pod: Optional[str] = Field(None, description="Pod名称"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:

    # ── Layer 4: 富 docstring(→ LLM 看到的 tool description)──
    """oomcheck(OOM 诊断)工具,用于分析和界定 OOM(Out of memory)问题。
    使用场景:
        1. Pod 被 OOMKilled
        2. 进程突然退出且 dmesg 有 oom-killer 记录
    仅支持节点诊断模式,channel 必须为 ecs。"""

    # ── Layer 5: try-execute-catch + 标准化错误响应 ──
    try:
        client = ClientFactory.create_client(uid=uid)
        helper = DiagnosisMCPHelper(client, timeout=150, poll_interval=1)
        params_obj = OOMCheckDiagnosisMCPRequestParams(...)
        response = await helper.execute(mcp_request)
        return response
    except Exception as e:
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败:{str(e)}",
            task_id=""
        )
```

**LLM 实际看到的 JSON Schema**(FastMCP 自动从 Field 生成):

```json
{
  "name": "oomcheck",
  "description": "oomcheck(OOM 诊断)工具...(完整 docstring)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "uid": {"type": "string", "description": "用户ID"},
      "region": {"type": "string", "description": "实例地域"},
      "channel": {"type": "string", "description": "诊断通道"},
      "instance": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "实例ID"},
      "pod": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "Pod名称"}
    },
    "required": ["uid", "region", "channel"]
  }
}
```

### 2.4 异步轮询模式(长任务必备)

诊断任务可能跑几十秒到几分钟,sysom_mcp 用**创建-轮询**模式:

```python
class DiagnosisMCPHelper:
    async def execute(self, request):
        # 1. 创建异步任务
        task_id = await self._create_task(request)
        # 2. 轮询结果(timeout=150s, interval=1s)
        result = await self._wait_for_result(task_id)
        return DiagnosisMCPResponse(task_id=task_id, result=result)
```

**借鉴点**:你的 Loki 查询如果跨多服务、时间长,用同样模式——立即返回 task_id,然后轮询。

### 2.5 多 FastMCP 实例合并(脆弱但实用)

`sysom_main_mcp.py` 把 8 个子模块的 FastMCP 实例合并成一个统一 server:

```python
mcp = FastMCP(name="SysOM Unified MCP Server")

from tools.am_mcp import mcp as am_mcp
from tools.mem_diag_mcp import mcp as mem_mcp
# ... 8 个模块

service_mcps = [am_mcp, mem_mcp, io_mcp, net_mcp, sched_mcp,
                other_mcp, crash_agent_mcp, initial_sysom_mcp]

for service_mcp in service_mcps:
    if hasattr(service_mcp, '_tool_manager'):
        for tool_name, tool_obj in service_mcp._tool_manager._tools.items():
            mcp.add_tool(tool_obj)
```

> ⚠️ **警告**:这段代码访问了 `_tool_manager._tools` 私有属性,FastMCP 升级可能直接挂掉。借鉴思路即可,**不要照抄实现**。

### 2.6 客户端集成

- **主**:Qwen Code(`~/.qwen/settings.json` 配置 `mcpServers`)
- **次**:Ollama(`ollama_agent.py` 用 `mcp.ClientSession` 直接连)
- **未验证**:Claude Desktop / OpenAI(代码里有 anthropic + openai 包,但无配置示例)

### 2.7 借鉴清单

| 借鉴点 | 实施难度 | 价值 |
|---|---|---|
| **Pydantic Field 自动生成 JSON Schema** | 低 | ⭐⭐⭐⭐⭐ |
| **docstring 写详细使用场景** | 低 | ⭐⭐⭐⭐⭐ |
| **tags 分类工具** | 低 | ⭐⭐⭐⭐ |
| **try-catch + 标准化错误响应** | 低 | ⭐⭐⭐⭐⭐ |
| **异步轮询模式(长任务)** | 中 | ⭐⭐⭐⭐ |
| **统一 server 合并多模块** | 中 | ⭐⭐⭐ |
| **访问 `_tool_manager._tools` 私有 API** | ❌ 别学 | 脆弱 |

---

## 模块 3 · AgentScope 2.0 — 全栈 Agent 平台

### 3.1 仓库元信息(已验证)

- **URL**: https://github.com/agentscope-ai/agentscope(`modelscope/agentscope` 已迁移并重定向)
- **Stars**: 27,084 · **语言**: Python · **License**: Apache 2.0
- **最新版**: v2.0.2(2026-06-16)
- **2.0 发布日**: 2026-05-25(v2.0.0)

### 3.2 2.0 真实新特性(已验证)

v2.0.0 changelog 列了 37 个 PR,核心变更:

| 特性 | 状态 | 备注 |
|---|---|---|
| **统一 `Agent` 类**(替代 `ReActAgent`) | ✅ | `reply()` + `reply_stream()` 取代 `__call__()` |
| **Event 系统**(typed stream) | ✅ | `AgentEvent` 替代 hook 机制 |
| **Middleware 系统** | ✅ | `MiddlewareBase` 替代 hook |
| **Permission 系统** | ✅ | `PermissionMode`(EXPLORE/BYPASS),tool-level ASK/ALLOW/DENY |
| **Workspace 系统** | ✅ | `LocalWorkspace` / `DockerWorkspace` / `E2BWorkspace` |
| **MCPClient**(原生 MCP) | ✅ | stateful/stateless 双模式,STDIO/HTTP/SSE |
| **FastAPI Multi-tenant Service** | ✅ | `create_app()` + 8 个 REST router + Redis 存储 |
| **WebUI**(React) | ✅ | 完整前端在 `examples/web_ui/` |
| **Skill 系统** | ✅ | 文件系统加载,打包成 ToolGroup |
| **Credential 模块** | ✅ | 与 model 解耦,JSON schema 可渲染表单 |
| **Context Compression** | ✅ | `trigger_ratio` + `reserve_ratio` + Offloader |
| **Agent Team**(v2.0.1) | ✅ | Leader spawns workers via `SubAgentTemplate` |
| **A2A 协议** | ❌ **不在 2.0** | 仅 1.x 实验,2.0 代码库无实现 |
| **RAG 模块** | ⚠️ 暂时移除 | 待重构,下版本回归 |
| **Memory 模块** | ⚠️ 暂时移除 | 与 agent 耦合,合并到 AgentState |

### 3.3 MCP 用法(已验证代码)

```python
from agentscope.agent import Agent
from agentscope.tool import Toolkit, Bash, Edit, Grep, Read, Write
from agentscope.mcp import MCPClient, HttpMCPConfig
from agentscope.model import DashScopeChatModel
from agentscope.credential import DashScopeCredential

agent = Agent(
    name="rca_agent",
    system_prompt="You are an SRE investigation agent...",
    model=DashScopeChatModel(
        credential=DashScopeCredential(api_key="YOUR_API_KEY"),
        model="qwen-max",
    ),
    toolkit=Toolkit(
        tools=[Bash(), Read(), Grep()],
        mcps=[
            MCPClient(
                name="prometheus",
                is_stateful=False,
                mcp_config=HttpMCPConfig(
                    url="https://your-prom-mcp.example.com/mcp",
                ),
            ),
        ],
        skills_or_loaders=["./skills"],
    ),
)
```

**关键设计**:`MCPClient` 直接进 `Toolkit`,**对 Agent 来说 MCP 工具和本地工具无差别**——同一调用接口。

### 3.4 并行工具调用(已验证实现)

工具在 `ToolBase` 上声明 `is_concurrency_safe: bool`:

```python
# src/agentscope/agent/_agent.py L1101
async def _batch_tool_calls(self):
    batches = []
    for tool_call in self._get_executable_tool_calls():
        tool = await self.toolkit.get_tool(tool_call.name)
        if tool.is_concurrency_safe:
            # 加入并发 batch
            ...
        else:
            # 单独 sequential batch
            ...
    return batches

# 并发执行
results = await asyncio.gather(
    *[self._into_queue(tc, queue) for tc in tool_calls],
    return_exceptions=True,
)
```

**亮点**:**失败不连坐**——`return_exceptions=True` 让一个工具挂掉不影响其他,异常汇总成 `ExceptionGroup` 抛出。

### 3.5 多租户 FastAPI Service(已验证)

```python
# examples/agent_service/main.py
from agentscope.app import create_app
from agentscope.app.message_bus import RedisMessageBus
from agentscope.app.storage import RedisStorage
from agentscope.app.workspace_manager import LocalWorkspaceManager

app = create_app(
    storage=RedisStorage(host="localhost", port=6379),
    message_bus=RedisMessageBus(host="localhost", port=6379),
    workspace_manager=LocalWorkspaceManager(
        basedir="./workspaces",
        default_mcps=[MCPClient(name="browser", mcp_config=...)],
    ),
)
```

**8 个 REST router**:`/agent` / `/chat` / `/sessions`(SSE 流)/ `/credential` / `/model` / `/schedule` / `/workspace` / `/tts_model`。

**多租户**:所有资源按 `user_id` 隔离(`X-User-ID` header)。

### 3.6 vs LangGraph 事实对比

| 维度 | AgentScope 2.0 | LangGraph |
|---|---|---|
| 核心范式 | ReAct 循环引擎(`Agent.reply()`) | 状态图(节点+边+条件) |
| Agent 定义 | 配置式(传参给 `Agent` 类) | 编程式(自己画 `StateGraph`) |
| 控制流 | 内置 ReAct 循环,无自定义拓扑 | 任意 DAG + 条件边 |
| 流式输出 | typed `AgentEvent` 流 | `astream_events()` |
| 状态管理 | `AgentState` Pydantic + Redis | `State` TypedDict + checkpointer |
| 工具并行 | 自动按 `is_concurrency_safe` 分批 | 手动 `Send` 或 `RunnableParallel` |
| MCP | ✅ **原生一等公民** | ⚠️ `langchain-mcp-adapters` 独立包 |
| HITL | Event 驱动(`RequireUserConfirmEvent`) | `interrupt_before` / `interrupt_after` |
| 服务部署 | ✅ **内置** FastAPI `create_app()` | ❌ 自己写或买 LangGraph Platform |
| 多租户 | ✅ 原生(user_id 隔离) | 手撸 |
| 沙箱执行 | ✅ Docker / E2B Workspace | ❌ 无 |
| 权限系统 | ✅ 内置(ASK/ALLOW/DENY) | ❌ 无 |
| Web UI | ✅ 仓库自带 React 前端 | ❌ 无 |
| 持久化 | Redis 内置 | 内存/SQLite/Postgres checkpointer |
| 成熟度 | v2.0(2026-05-25,1 个月新) | 生产稳定,广泛使用 |
| License | Apache 2.0 | MIT |

### 3.7 借鉴清单

| 借鉴点 | 实施难度 | 价值 |
|---|---|---|
| **`is_concurrency_safe` 标记工具** | 低 | ⭐⭐⭐⭐ |
| **失败不连坐(ExceptionGroup)** | 低 | ⭐⭐⭐⭐ |
| **Toolkit 统一抽象本地工具+MCP 工具** | 中 | ⭐⭐⭐ |
| **Permission 系统(ASK/ALLOW/DENY)** | 中 | ⭐⭐⭐ |
| **Workspace 沙箱隔离** | 高 | ⭐⭐ |
| **Context Compression(trigger_ratio)** | 中 | ⭐⭐⭐ |
| **整套 AgentScope 部署** | ❌ 切换成本高 | 不建议 |

---

## 模块 4 · RCA Demo 落地建议(只借鉴,不照搬)

### 4.1 一周内可行的"借鉴套餐"

**架构**:LangGraph 状态机(8 节点)+ 硅基流动 DeepSeek-V3 + ChromaDB

**借鉴 UModel 的**:
1. **YAML 化 topology**(必做)——给每个服务定义:
   - `depends_on`(上下游)
   - `metrics`(预生成 PromQL,LLM 只填 service_id)
   - `logs`(预定义 LogQL 模板)
2. **Skill prompt 内嵌完整协议**(必做)——把 RCA 5 步法写进 system prompt
3. **Observation 模式**(可选)——给 3 个演示场景预定义"该查什么"
4. **Red Herring 测试**(可选)——故意放干扰项,演示时强调"Agent 没被骗"

**借鉴 sysom_mcp 的**:
1. **Pydantic Field 生成 JSON Schema**(必做)——Function Calling 工具定义全部用 Field
2. **富 docstring**(必做)——每个工具描述写清楚使用场景、限制、返回格式
3. **try-catch 标准化错误**(必做)——工具挂了返回结构化错误,不让 LLM 自由解释
4. **tags 分类**(可选)——`prometheus_tools` / `loki_tools` / `topology_tools`

**借鉴 AgentScope 2.0 的**:
1. **`is_concurrency_safe` 标记**(可选)——查 Prometheus 和查 Loki 可以并行
2. **失败不连坐**(必做)——一个工具挂了不阻塞其他

### 4.2 不要做的

| 不要 | 原因 |
|---|---|
| 部署完整 UModel(Go + Docker compose) | 太重,一周做不完 |
| 用 AgentScope 替换 LangGraph | 切换成本高,且你已经定了 LangGraph |
| 实现 A2A 协议 | AgentScope 2.0 都没做,你做啥 |
| 实现 Runbook 6 类全集 | 只用 observations + skills 两类够了 |
| 用 FastMCP `_tool_manager._tools` 私有 API | 脆弱,直接用 LangChain Tool 抽象 |
| 上 Permission 系统 | Demo 不需要,Demo 不需要,Demo 不需要 |

### 4.3 关键架构图(借鉴后)

```
┌────────────────────────────────────────────────────────────┐
│  topology.yaml(UModel 借鉴)                               │
│  ├── services:                                             │
│  │   order-service:                                        │
│  │     depends_on: [mysql, redis]                          │
│  │     metrics:                                            │
│  │       latency_p95: 'histogram_quantile(...)'  ← 预生成  │
│  │       error_rate: 'rate(...{status=~"5.."}[5m])'        │
│  │     logs:                                               │
│  │       errors: '{app="order-service"}|="ERROR"'          │
│  └── runbook:                                              │
│      oom_observation:                                      │
│        steps: [查 pod 内存, 查 node 内存, 查 GC 日志]    │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────┐
│  LangGraph 8 节点状态机                                     │
│  告警接收 → 聚合 → 拓扑关联 → 指标 → 日志 → 案例 → 根因 → 报告 │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────┐
│  Tools(sysom_mcp 借鉴:Pydantic Field + 富 docstring)       │
│  ├── query_prometheus(service_id, metric_name)              │
│  │   ↑ 不传 PromQL,只传 service_id + metric_name            │
│  │   ↑ 内部用 topology.yaml 里的 generator 查               │
│  ├── query_loki(service_id, log_type)                       │
│  ├── search_incidents(query, top_k=5)                       │
│  └── get_topology(service_id, direction=upstream)           │
└────────────────────────────────────────────────────────────┘
```

**核心借鉴**:**LLM 永远不直接写 PromQL/LogQL**,只传 `service_id` + `metric_name`。这把幻觉风险降到最低——模型不会编造不存在的指标名。

---

## 速记卡

### 5 个必背纠正(现有 reference-alibaba-rca.md 的错误)

| 原文 | 实际 |
|---|---|
| UModel "三类节点 EntitySet/TelemetryDataSet/Storage" | ❌ 实际 9 dataset kinds + 7 storage kinds,"TelemetryDataSet" 不是字面 kind |
| UModel "四类关系" | ❌ 实际 6 link kinds(漏了 entity_source_link / runbook_link) |
| Runbook "5 类:Observation/Toolkit/Knowledge/Automation/Skill" | ⚠️ 实际 6 类,actions 漏了,knowledge 已 deprecated |
| AgentScope 2.0 有 A2A 协议 | ❌ 不在 2.0 代码库(1.x 实验) |
| UModel 是 RCA 算法实现 | ❌ 是语义层,推理在 LLM Skill prompt |

### 5 个借鉴口诀

1. **YAML 写拓扑,LLM 不写 PromQL** —— UModel 的 token 化查询
2. **Pydantic Field + 富 docstring + try-catch** —— sysom_mcp 工具定义三件套
3. **Skill prompt 内嵌完整诊断协议** —— UModel 的 SKILL.md 思路
4. **工具标 `is_concurrency_safe` 自动并行** —— AgentScope 2.0 的 batching
5. **失败不连坐(ExceptionGroup)** —— AgentScope 2.0 的容错

### 10 个值得抄的具体设计

1. UModel:metric `generator` 字段——预生成 PromQL,token 化 `$service_id`
2. UModel:`golden_metric: true` 标记——告诉 LLM 哪些指标重要
3. UModel:`confirmation_required: true`——高风险操作 Human-in-the-loop
4. UModel:Red Herring 测试集——测 Agent 证伪能力
5. UModel:Skill 内嵌完整 SKILL.md(5 phase 协议)
6. sysom_mcp:`@mcp.tool(tags={"..."})` 分组
7. sysom_mcp:docstring 含"使用场景"+"限制"+"返回格式"三段
8. sysom_mcp:DiagnosisMCPHelper 异步轮询模式(timeout=150s)
9. AgentScope:`is_concurrency_safe` 自动 batching
10. AgentScope:`asyncio.gather(return_exceptions=True)` 失败不连坐

### 比赛理论加分点

如果评委问"参考了哪些业界实践",可以答:

> "参考了阿里 UnifiedModel 的 Ontology 建模思路——把运维实体、指标、日志抽象成对象图,让 LLM 通过结构化查询而非自由生成 PromQL;借鉴了 sysom_mcp 的工具封装范式——Pydantic Field 自动生成 JSON Schema + 富 docstring 引导 LLM 调用;对比了 AgentScope 2.0 和 LangGraph 后,选 LangGraph 因为 RCA 是固定 8 步状态机,不需要 ReAct 自由循环。"

这套答法既显示调研深度,又解释了选型理由。
