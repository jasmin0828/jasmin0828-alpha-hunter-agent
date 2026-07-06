# Daily Scan Report

Daily Scan Report 是 Alpha Hunter Market System 的中文每日扫链报告。

它的目标是把当天系统已经观察到的扫链结果整理成一份人可读的
Markdown 文件，方便后续 Telegram、Email、Obsidian 或其他 Delivery
Layer 复用。

## 目的

Daily Scan Report 用于回答：

- 今天系统是否正常运行
- 今天扫描了哪些链
- 今天扫描了多少 Token
- 今天产生了多少 Signal
- 今天有哪些高交易量记录
- 今天有哪些新增 Candidate
- 今天 Theme 分布如何
- 今天 run log 是否完整

## 与 Market Analysis 的区别

Daily Scan Report 不是 Market Analysis。

它只描述系统扫描结果，不解释市场，不预测，不生成投资观点。

| Daily Scan Report | Market Analysis |
| --- | --- |
| 描述扫描结果 | 解释市场含义 |
| 汇总 run log | 判断叙事强弱 |
| 展示 Token / Signal / Theme 统计 | 形成研究观点 |
| 展示数据完整性 | 给出下一步研究假设 |
| Observe, don't interpret | Interpret with evidence |

当前版本只实现 Daily Scan Report。

## 数据来源

当前初稿读取本地 SQLite 数据：

- `data/alpha_hunter.db`
- `scan_runs`
- `token_snapshots`
- `signal_events`

它不修改数据库，不新增 schema，不改变 scanner、ranking、evidence 或
report runtime。

## 报告输出

默认输出路径：

```text
reports/daily_scan_report.md
```

该文件属于运行产物，默认不提交到 Git。

## 报告结构

报告包含：

1. 今日运行概况
2. 扫描概况
3. 24H 交易量 TOP10
4. Social Heat TOP10
5. Evidence Score TOP10
6. 今日新增 Candidate
7. Theme 分布
8. 较昨日变化
9. 系统运行记录
10. 数据完整性检查

## Observe, Don't Interpret

Daily Scan Report 的核心原则是：

```text
Observe, don't interpret.
```

允许写入：

- 扫描数量
- 链分布
- Signal 数量
- Theme 数量
- TOP 表格
- Run log 状态
- 数据完整性状态

不允许写入：

- 投资建议
- 买卖判断
- 价格预测
- 目标价
- 自动交易动作
- 钱包或私钥相关逻辑
- 外部 LLM 解释

## Safety Boundary

Daily Scan Report 保持 Alpha Hunter 当前安全边界：

- read-only
- no trading
- no wallet connection
- no private key
- no signing
- no swaps
- no automated execution
- no financial advice

## Future Delivery Layer

这份 Markdown 可以作为未来统一输出格式，用于：

- Telegram Delivery Layer
- Email Delivery Layer
- Obsidian Sync
- Weekly Review
- Monthly Review

任何 Delivery Layer 都应只转发报告内容，不改变 scanner、ranking、
evidence、database schema 或交易边界。
