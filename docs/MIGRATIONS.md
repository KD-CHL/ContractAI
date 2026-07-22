# ContractGuard SQLite 迁移、备份与回滚

ContractGuard 的 SQLite 结构由独立迁移工具管理。应用发布时应先停止写入、备份数据库、执行迁移，再启动新版本。迁移脚本不会读取应用密钥，也不会保存合同明文到日志。

## 当前版本

- V1 `baseline_contractguard`：无损兼容原有 `reviews`、`review_feedback`、`memories` 三张表。旧数据库没有 `schema_migrations` 时，工具只执行 `CREATE ... IF NOT EXISTS` 和结构校验，不删除、不复制、不改写已有业务行。
- V2 `identity_audit_review_lifecycle`：新增 `organizations`、`users`、`auth_sessions`、`audit_logs`、`finding_actions`；为 `reviews` 增加创建人、软删除、人工决策状态、状态版本、分析版本和幂等键，并增加工作台查询索引。已有 `org_id` 会回填到 `organizations`。
- V3 `operational_work_items`：新增 `work_items` 和 `work_item_events`，把已完成审阅中的风险与义务转为可指派、可设截止时间、可留处置备注并带状态版本的工作项。迁移会按 `review_id + kind + source_ordinal` 幂等回填已有完成报告，并为每项写入一条 `materialized` 初始事件；不会复制原始文件或抽取全文。

`users.email` 在整个部署中使用大小写不敏感的全局唯一索引，因此 `Legal@Example.com` 与 `legal@example.com` 不能属于两个不同账号。这避免 email+password 登录时出现跨组织歧义。

## V3 业务状态、API 与权限

V3 把不可变的分析结果和可变的人工处置状态分开：`work_items.source_payload_json` 保留报告中对应风险或义务的数据和必要证据片段；负责人、截止时间、备注、状态与事件单独更新。所有工作项和审批写操作都使用 `state_version`/`expected_version` 乐观锁，旧版本写入返回 `409`，避免成员之间静默覆盖。

- 风险工作项从 `open` 开始，可进入 `in_progress`、`resolved` 或 `accepted`；解决或接受风险必须有说明。义务工作项从 `pending` 开始，可进入 `in_progress`、`completed` 或 `waived`；豁免必须有说明。终态可以回到各自初始状态重新处置。
- 审阅审批使用 `draft -> in_review -> approved|rejected`；`rejected` 可重新提交，`approved` 只有 owner/admin 可以重新打开。存在未解决或未接受的 high/critical 风险工作项时不能批准。
- owner/admin 可指派和更新组织内工作项、接受风险、豁免义务并做最终审批；reviewer 只能领取给自己、更新本人负责的工作项，并把 `draft` 或 `rejected` 提交为 `in_review`；viewer 只有读取权限。
- 读取入口为 `GET /operations/summary`、`GET /work-items`、`GET /reviews/{id}/work-items` 和 `GET /work-items/{id}/events`；写入入口为 `PATCH /work-items/{id}` 与 `PATCH /reviews/{id}/decision`。路径均位于配置的 API 前缀下，默认是 `/api/v1`。

## 命令

以下命令均从项目根目录执行。

查看状态；数据库不存在时只报告状态，不会创建文件：

```bash
python scripts/manage_db.py status --database data/contractguard.db
```

创建一致性备份。目标文件已存在时命令会拒绝覆盖：

```bash
python scripts/manage_db.py backup \
  --database data/contractguard.db \
  --destination backups/contractguard-before-v3.db
```

升级到最新版本：

```bash
python scripts/manage_db.py upgrade --database data/contractguard.db
```

恢复或回滚到一份已验证备份：

```bash
python scripts/manage_db.py restore \
  --backup backups/contractguard-before-v3.db \
  --destination data/contractguard.db
```

恢复前必须停止 ContractGuard 进程。工具会尝试取得 SQLite 独占维护锁；数据库繁忙时直接失败。若目标数据库已经存在，工具会先在同目录自动创建：

```text
contractguard.db.pre-restore-YYYYMMDDTHHMMSSZ-XXXXXXXX.bak
```

只有备份源、自动安全快照和待替换的临时数据库均通过 SQLite `quick_check` 后，才会原子替换目标文件。命令输出中的 `safety_backup` 是恢复前状态的位置，必须保留到业务验收完成。

## 推荐发布流程

1. 停止 Web/worker 写入并确认没有长事务。
2. 执行 `status`，记录当前版本。
3. 执行 `backup`，把输出中的 SHA-256、文件大小和 schema version 写入发布记录。
4. 将备份复制到与主机故障域不同、受访问控制的存储，并做一次恢复演练。
5. 执行 `upgrade`；同一命令可安全重复运行，已登记版本会校验 checksum 后跳过。
6. 再次执行 `status`，运行 API 冒烟测试和数据抽样核对。
7. 启动新版本并监控错误、延迟、数据库空间与锁等待。

## 回滚策略

本项目不提供会 `DROP TABLE` 或丢弃新字段的自动 down migration。原因是 V2/V3 上线后可能已经写入用户、会话、审计、工作项、处置事件、负责人、截止时间和审批状态，直接回退 DDL 会静默丢失这些记录。

需要回滚时优先恢复发布前备份：停止应用，先另存当前故障现场，再使用 `restore`。`restore` 自身还会生成一份 `pre-restore` 安全快照，所以新版本运行期间产生的数据不会被无提示覆盖。恢复旧备份会让数据库回到备份时点，备份之后新增或变更的工作项、事件和审批决定不会出现在恢复后的库中；若必须把这些数据合并回旧备份，应从故障现场快照编写一次性、经过审阅的数据迁移，而不是修改通用恢复工具。

## Python 接线

应用启动器或部署任务可以直接使用稳定公开 API：

```python
from contract_guard.infrastructure.db import (
    backup_database,
    migration_status,
    restore_database,
    upgrade_database,
)

status = migration_status("data/contractguard.db")
backup = backup_database("data/contractguard.db", "backups/pre-release.db")
result = upgrade_database("data/contractguard.db")
# rollback = restore_database("backups/pre-release.db", "data/contractguard.db")
```

生产部署应由单独的 release job 执行迁移，不应让多个 Web 副本同时负责升级。虽然迁移器使用 `BEGIN IMMEDIATE` 并会在并发情况下重新检查版本，集中式发布步骤仍更容易审计和恢复。
