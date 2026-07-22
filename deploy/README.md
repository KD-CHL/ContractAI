# ContractGuard 部署说明

当前可落地基线是“单实例应用 + SQLite 持久卷”。它包含本地账号认证、RBAC、审阅历史和审计日志，但不是多副本 SaaS 基础设施。审阅仍在 HTTP 请求内同步完成；项目没有异步任务队列、跨副本 Redis 状态、Prometheus 指标或自动告警。

## Docker Compose

默认只需启动 `app`：

```bash
docker compose up --build
```

宿主机默认访问 `http://127.0.0.1:8010`。SQLite 位于命名卷 `contractguard-data`。首次打开页面时创建组织和 owner 账号；密码至少 12 位，并需覆盖大小写字母、数字、符号中的至少三类。

Compose 不会自动读取 `.env.local`。需要 AI 增强时显式传入：

```bash
docker compose --env-file .env.local up --build
```

`docker-compose.yml` 中的 Redis、Kafka、Neo4j、MySQL 和 Milvus profile 只用于适配器研发时启动依赖。当前应用启动路径不会连接这些容器，也不会因此获得队列、分布式缓存、MySQL 仓储或图谱能力；功能验收和生产部署都不应把启动 profile 当作集成完成。

## SQLite 发布与回滚

应用会在启动时执行幂等升级；正式发布仍应先停止写入并独立备份、迁移：

```bash
make db-status
make db-backup BACKUP=backups/pre-release.db
make db-upgrade
```

回滚必须先停止应用：

```bash
make db-restore BACKUP=backups/pre-release.db
```

恢复工具会先保存当前数据库的安全快照，并验证 SQLite 完整性。完整规则见 [`../docs/MIGRATIONS.md`](../docs/MIGRATIONS.md)。软删除只是把审阅移入回收站，不会缩小数据库或备份；永久保留期仍需由部署方制定。

## Kubernetes 基线

[`kubernetes/contractguard.yaml`](kubernetes/contractguard.yaml) 提供单副本起点：

- 固定 UID/GID 10001 的非 root 容器；
- 只读根文件系统和 SQLite PVC；
- init container 在启动前执行版本化迁移；
- `/live` 用于存活探针，`/ready` 用于就绪探针；
- 默认要求登录，首次空库仍可创建 owner，之后关闭公开组织注册；
- `Secure` 会话 Cookie 默认开启，因此必须由 Ingress 或网关提供 HTTPS。

部署前必须替换两处示例镜像地址，并确保 init container 与应用使用同一个不可变镜像摘要。清单不包含 Ingress、TLS 证书、Secret 内容、备份任务或监控系统。

混合模式所需的 `OPENAI_API_KEY`、可选 `LIGHTRAG_API_KEY` 应由 External Secrets、Sealed Secrets 或云密钥服务创建为 `contractguard-secrets`，不要写进 ConfigMap 或镜像。`/ready` 只检查本地存储与必需配置是否存在，不会向 OpenAI 或 LightRAG 发起探测；外部依赖的真实可达性仍需平台侧合成探测。

不要把 Deployment 副本数提高到 1 以上。当前 SQLite 文件、本地会话、进程内缓存和同步审阅路径没有多副本一致性保证。若未来替换持久化和会话实现，应先完成迁移、并发、租户隔离和故障恢复验证，再调整拓扑。

## 上线清单

1. 固定基础镜像与应用镜像摘要，运行 CI、SBOM 和漏洞扫描。
2. 备份 SQLite，并在隔离环境完成一次恢复演练。
3. 通过 HTTPS 暴露服务；保留 `CONTRACT_GUARD_AUTH_COOKIE_SECURE=true`。
4. 保持 `CONTRACT_GUARD_AUTH_REQUIRED=true`；首个 owner 注册完成后确认公开注册关闭。
5. 按业务限制上传字节数、页数、字符数、DOCX 解压体积和 OCR 像素。
6. 将应用 JSON 请求日志接入平台日志系统；当前项目不自带指标采集和告警。
7. 为合同正文、软删除记录、审计日志和备份分别制定访问、加密、保留与销毁策略。
8. 在混合模式验证模型失败行为；模型调用失败不会被伪装成完整 AI 审阅。
