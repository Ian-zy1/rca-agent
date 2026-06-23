# 可观测性地基 + 故障模式库（RCA 的领域命脉）

> 这是 RCA agent 的**领域知识**——不学这个，agent 不知道"该看什么指标、什么样的值算异常、根因可能在哪"。所有内容锚定你的真实 VictoriaMetrics（ES/MySQL/Redis/Kafka 主机），不用 K8s 例子。

## 第一部分：可观测性词汇（比赛高频 + agent 认知地基）

### 三支柱（Metrics / Logs / Traces）

| 支柱 | 是什么 | 你的 VM 里有吗 |
|---|---|---|
| **Metrics** | 随时间变化的数值（CPU、内存、QPS）| ✅ VictoriaMetrics |
| **Logs** | 带时间戳的离散事件文本 | ⚠️ 需 Loki（你栈里暂缺，可后补）|
| **Traces** | 单个请求跨服务的因果链 | ❌ 传统主机栈通常没有 |

> RCA agent 主要靠 Metrics + Logs。Traces 在微服务栈才有——你这套主机/中间件监控用不上，比赛知道概念即可。

### SLI / SLO / SLA（必考）

- **SLI**（Service Level Indicator）：**测量出来的指标**。如"p99 延迟""成功率"
- **SLO**（Objective）：**SLI 的目标**。如"p99 < 300ms，99.9% 的时间满足"
- **SLA**（Agreement）：**带违约后果的合同**（对外承诺）

**Error budget（错误预算）= 1 − SLO**。SLO 99.9% → 每月允许 43 分钟故障。**预算烧得快 = 出事了，该 RCA。** 这是 RCA agent 的触发逻辑之一。

### 四黄金信号（Google SRE，必考）

用户态服务**只看四样**：
1. **延迟 Latency**（p95/p99，区分成功/失败请求）
2. **流量 Traffic**（QPS/并发）
3. **错误 Errors**（5xx/失败率）
4. **饱和度 Saturation**（还能扛多少，队列/in-flight）

### RED vs USE（选哪个看层）

| 方法 | 适用层 | 看什么 | 创始人 |
|---|---|---|---|
| **RED** | 服务（SaaS/应用）| Rate / Errors / Duration | Tom Wilkie |
| **USE** | 资源（IaaS/主机）| Utilization / Saturation / Errors | Brendan Gregg |

> **agent 的认知脊柱**：SaaS 用 RED 看症状 → PaaS 看中间件指标 → IaaS 用 USE 找资源瓶颈。**这条因果梯就是 RCA 的主干**（你的跨层场景正踩着它）。

权威：[SRE Book Ch.6 监控](https://sre.google/sre-book/monitoring-distributed-systems/)、[USE Method (Brendan Gregg)](https://www.brendangregg.com/usemethod.html)、[RED Method (Grafana)](https://grafana.com/blog/the-red-method-how-to-instrument-your-services/)

---

## 第二部分：故障模式库（agent 该看什么指标判定什么根因）

这是 RCA agent 的**领域知识核心**——把"症状 → 该查的指标 → 可能根因"焊成对照表（也是 002 FC 节"场景→指标约束"的素材来源）。

### IaaS / 主机层（用 USE 方法）

| 症状 | 该查的指标 | 可能根因 |
|---|---|---|
| 主机内存耗尽 | `node_memory_MemAvailable_bytes` → 0；swap `si/so` | 进程泄漏/缓存膨胀 → OOM killer 杀进程 |
| CPU 饱和 | load avg > 核数；`node_cpu_seconds_total{mode="idle"}` 趋零；steal>0 | 计算密集/上下文爆炸 |
| 磁盘 IO 满 | `node_disk_io_time_seconds_total` (%util 趋 100)；iowait | 大量 fsync/全表扫描/日志风暴 |
| 磁盘空间满 | `node_filesystem_avail_bytes` → 0 | **ES/Kafka/MySQL 写入瞬间全挂**（最致命）|

### PaaS / 中间件层（你的主战场）

**MySQL**（`mysql_global_status_*`）
| 症状 | 指标 | 根因方向 |
|---|---|---|
| 下单慢 | `threads_connected` 逼近 max；`slow_queries` rate 飙 | 慢 SQL 占连接池 |
| **锁等待**（你 D1 跑出来的真 case）| `innodb_row_lock_time` 累计高 / `innodb_row_lock_waits` | 长事务持锁、锁粒度过大 |
| 缓冲池压力 | `innodb_buffer_pool_wait_free` | 缓冲池太小 / 大量磁盘读 |
| 主从延迟 | `seconds_behind_master` | 大事务 / 从库 IO 不够 |

**Redis**（`redis_*`）
| 症状 | 指标 | 根因方向 |
|---|---|---|
| 读写偶发失败 | `used_memory` 逼近 `maxmemory`（你的 maxmemory=0 ⚠️无上限）| **大 key 膨胀 → RSS 吃光主机内存被 OOM killer 杀** |
| 驱逐风暴 | `evicted_keys` 涨 | 内存满 + 淘汰策略 |
| 延迟尖刺 | `latency_percentiles_usec` | 大 key 操作阻塞 / fork 持久化 |
| 连接被拒 | `rejected_connections` | maxclients 满 |

**Elasticsearch**（`elasticsearch_*`，你的 `cluster=heimdall-es`）
| 症状 | 指标 | 根因方向 |
|---|---|---|
| 搜索慢 | `jvm_memory_used_bytes{area=heap}` > 75% → 老 GC 频繁 | **堆泄漏 / 大聚合** |
| 查询被拒 | thread_pool `rejected`（search/write 队列溢出）| 并发过高 → es_rejected_execution (429) |
| 集群红/黄 | cluster_status；unassigned_shards | 节点掉线 / 磁盘 >85% 触发只读 |
| GC 卡顿 | `jvm_gc_collection_seconds`（old gen）| 堆分配不足 / 内存泄漏 |

**Kafka**
| 症状 | 指标 | 根因方向 |
|---|---|---|
| 业务感知"延迟" | **消费积压** = `log_end_offset − current_offset`（按 group/partition）| 消费者处理太慢 / 分区不均 |
| 数据丢失风险 | `under_replicated_partitions` > 0 | 副本同步跟不上 |
| 重平衡风暴 | GC 暂停 > poll.interval.ms | 消费者被踢出组 |

### SaaS / 应用层（用 RED）

| 症状 | 指标 | 根因方向 |
|---|---|---|
| 错误率飙升 | 5xx rate；成功率跌破 SLO | 下游故障 / 代码 bug / 限流触发 |
| 延迟劣化 | `histogram_quantile(0.95, ...)` 超 SLO | 下游慢 / 资源饱和 |
| 饱和点 | in-flight 请求升 + 吞吐平 + 延迟升 = 到瓶颈 | 容量不够 |

---

## 第三部分：RCA 的因果梯（agent 主循环）

```
SaaS RED 异常（症状）           ← 用户/告警从这里进
   ↓ "为什么会这样？"
PaaS 中间件指标异常（近因）     ← 查 MySQL/Redis/ES 指标
   ↓ "中间件为什么异常？"
IaaS 主机 USE 异常（根因）      ← 查主机 CPU/内存/IO/磁盘
   ↓ 结论
根因 + 证据 + 建议
```

> **这就是你的 8 节点工作流的"灵魂"**。LangGraph 把它画成状态图，但内核是这条因果梯。每个 RCA 场景（MySQL 锁/Redis OOM/ES 堆泄漏）都是沿着它往下钻。

---

## 速记卡

| 要点 | 内容 |
|---|---|
| 三支柱 | Metrics / Logs / Traces（你栈里主要是 Metrics）|
| SLI/SLO/SLA | 指标 / 目标 / 合同；error budget = 1 − SLO |
| 四黄金信号 | 延迟/流量/错误/饱和度 |
| RED | 服务层（Rate/Errors/Duration）|
| USE | 资源层（Utilization/Saturation/Errors）|
| 因果梯 | SaaS症状 → PaaS近因 → IaaS根因 |
| MySQL 锁 | `innodb_row_lock_time` / `innodb_row_lock_waits`（你 D1 真跑过）|
| Redis OOM | maxmemory=0 无上限 → RSS 吃光主机内存 |
| ES 堆 | `jvm_memory_used_bytes{area=heap}` > 75% → GC 风暴 |

### 比赛理论题预测（可观测性向）

1. **Metrics/Logs/Traces 三支柱区别？RCA 主要靠哪个？**
2. **SLI/SLO/SLA 区别？什么是 error budget？**
3. **Google 四黄金信号是哪四个？**
4. **RED 和 USE 方法的区别？分别用于哪一层？**
5. **MySQL 慢查询可能有哪些根因？看什么指标？**（连接池/锁/缓冲池）
6. **为什么 Redis maxmemory=0 是隐患？**（无上限 → OOM killer）
7. **RCA 的"因果梯"为什么从 SaaS 往 IaaS 钻？**（症状在下层、根因在上游资源）

---

> **读完这个，agent 该查什么、什么值算异常、根因往哪找——你心里有谱了。** 这套故障模式库直接当 D5「指标分析」节点的 system prompt 素材。
