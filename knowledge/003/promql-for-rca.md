# PromQL / MetricsQL for RCA

> D3 你要写真 `query_prometheus()` 工具，喂它的查询语句就是 PromQL。你的后端是 VictoriaMetrics（说 **MetricsQL**，PromQL 超集）。本文讲 RCA 常用的查询模式，**全是能直接抄进 topology.yaml 的语句**。

## 模块 1：指标类型（用错查询就错）

| 类型 | 特征 | RCA 注意 |
|---|---|---|
| **Counter** | 只增不减（如 `slow_queries` 累计值）| **必须用 rate()/increase()，不能裸查**——你 D1 跑出 180万 就是裸查 counter，意义不大 |
| **Gauge** | 可增可减（如 `threads_connected`、`memory_used`）| 可裸查瞬时值 |
| **Histogram** | 分桶（`*_bucket`），算分位数用 | 算 p95 延迟用 `histogram_quantile` |

> 你 D1 那条 `mysql_global_status_slow_queries` = 1580 是 **Counter 裸查**——RCA 里要么 `rate(...[5m])` 看速率，要么 `increase(...[1h])` 看增量。这是新手最常踩的坑。

## 模块 2：五个必会函数

### rate() —— counter 的速率（最常用）
```promql
rate(mysql_global_status_slow_queries{instance="10.3.240.116:19211"}[5m])
# 过去5分钟平均每秒慢查询数
```

### increase() —— 窗口内增量
```promql
increase(mysql_global_status_slow_queries{instance="..."}[1h])
# 过去1小时新增了多少慢查询
```

### histogram_quantile() —— 算分位数（延迟必备）
```promql
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{instance="..."}[5m])) by (le)
)
# p95 延迟。注意一定要 sum by (le) 再 quantile
```

### topk() —— 找最严重的几个（RCA 排名）
```promql
topk(5, rate(node_cpu_seconds_total{mode!="idle"}[5m])) by (instance)
# CPU 最高的 5 台主机——优先排查
```

### offset / @ —— 基线对比（异常检测核心）
```promql
rate(http_requests_total[5m]) - rate(http_requests_total[5m] offset 1d)
# 当前 QPS 减去昨天同时刻 → 异常增量。正值=比昨天高
```

## 模块 3：RCA 常用查询模式（直接抄）

### 模式 A：Top Offenders（谁最该查）
```promql
# 内存最高的5台主机
topk(5, node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)
# 慢查询最多的3个MySQL实例
topk(3, rate(mysql_global_status_slow_queries[5m]))
```

### 模式 B：基线 diff（异常多严重）
```promql
# Redis 内存比一周前涨了多少
redis_memory_used_bytes - redis_memory_used_bytes offset 7d
```

### 模式 C：饱和度（还能扛多少）
```promql
# MySQL 连接池饱和度
mysql_global_status_threads_connected / mysql_global_variables_max_connections
# > 0.8 = 危险
```

### 模式 D：错误率
```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))
# 5xx 占比
```

### 模式 E：消费积压（Kafka 专属）
```promql
sum by (consumergroup, topic)(
  kafka_consumergroup_lag
)
# 哪个消费组积压最严重
```

## 模块 4：VictoriaMetrics 特有（MetricsQL 比 PromQL 多的）

你的后端是 VM，它说 MetricsQL。**PromQL 语句全兼容**，外加几个好用扩展：

| MetricsQL 扩展 | 作用 |
|---|---|
| `histogram_over_time(gauge[t])` | 把 gauge 时间序列转成 histogram（VM 独有，PromQL 做不到）|
| `range_first/range_last` | 窗口首/末值 |
| `keep_metric_names` | 聚合后保留指标名 |
| `increase()` 更准 | VM 包含窗口前最后一个样本，比 Prometheus 更精确 |

> Demo 加分点：能说出"VM 的 increase() 比 Prometheus 更准（包含窗口前最后样本）"——体现你对真实后端的了解。

## 模块 5：两个 API 端点（agent 的查询原语）

| 端点 | 用途 |
|---|---|
| `/api/v1/query?query=...&time=...` | **瞬时查询**（某一时刻的值）——你 D1 用的就是这个 |
| `/api/v1/query_range?query=...&start=...&end=...&step=...` | **范围查询**（一段时间内的序列）——画趋势图/算增量用 |

你 D1 的 `query_prometheus()` 打的是 instant query。**RCA 常需要趋势**（"内存过去1小时怎么涨的"），那时改用 query_range。VictoriaMetrics 路径前缀是 `/select/0/prometheus/`（多租户）。

## 模块 6：标签匹配（你的真实标签）

```promql
# instance 精确匹配（你的主键）
mysql_global_status_threads_connected{instance="10.3.240.116:19211"}

# cluster 匹配（ES 用）
elasticsearch_jvm_memory_used_bytes{cluster="heimdall-es",area="heap"}

# 正则匹配多个
node_memory_MemAvailable_bytes{instance=~"10\\.2\\..*"}
```

---

## 给 D3 的建议：query_prometheus() 怎么写得靠谱

```python
@tool
def query_prometheus(promql: str) -> str:
    """查 VictoriaMetrics 指标。输入 PromQL。
    瞬时值用 /query；要看趋势改用 query_range。
    counter 类指标请用 rate()/increase()，不要裸查。"""
    r = requests.get(f"{PROM}/query", params={"query": promql},
                     auth=AUTH, verify=False, timeout=15)
    data = r.json()["data"]["result"]
    if not data:
        return "空结果（检查指标名/标签/时间窗口）"
    return json.dumps(data, ensure_ascii=False)[:500]
```
**description 里那句"counter 请用 rate()"**——就是治你 D1"裸查 counter"的毛病，让模型自己写对查询。这正是 002 FC 节讲的"description 决定智能程度"。

---

## 速记卡

| 要点 | 内容 |
|---|---|
| Counter | 只增，**必须 rate/increase**，不能裸查 |
| Gauge | 可裸查瞬时值 |
| rate vs increase | rate=每秒速率；increase=窗口总增量 |
| histogram_quantile | 算 p95/p99，要 `sum by (le)` 先聚合 |
| topk | 找最严重的 N 个，RCA 排名 |
| offset | 对比基线（昨天/上周），异常检测 |
| 两端点 | query(瞬时) / query_range(趋势) |
| VM 路径 | `/select/0/prometheus/api/v1/` |

### 比赛理论题预测

1. **Counter 和 Gauge 区别？为什么 Counter 要用 rate？**（只增；裸查是累计无意义）
2. **怎么算 p95 延迟？**（histogram_quantile + sum by le）
3. **topk 在 RCA 里干什么？**（找最严重的 N 个，优先排查）
4. **怎么做异常检测的基线对比？**（offset 昨天同时刻）
5. **VictoriaMetrics 和 Prometheus 的 MetricsQL 有何不同？**（超集；increase 更准；histogram_over_time）

---

> **读完这个，D3 的 query_prometheus() 你能写出靠谱版，topology.yaml 的 metrics 字段你也会填对 rate/increase 了。**
