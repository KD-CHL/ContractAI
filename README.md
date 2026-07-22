# ContractGuard

ContractGuard 是一个可直接运行的合同预审与风险处置工作台。它把本地账号与权限、合同解析、确定性规则、可选 OpenAI 复核、可追溯证据、风险与义务工作项、审批闭环和 SQLite 数据治理组织成一条完整流程，帮助法务与业务人员从定位问题继续推进到明确处置结果。

本轮架构、数据库、权限、接口、验证和剩余风险的完整记录见 [`docs/REFACTOR_REPORT.md`](docs/REFACTOR_REPORT.md)。

> **法律免责声明：** 本项目、演示规则、知识条目、示例合同和系统输出仅用于软件开发与辅助预审，不构成法律意见或律师服务。自动分析可能遗漏风险或产生误报，不能作为签署、诉讼、合规或其他高风险决定的唯一依据。

## 当前可用能力

- 默认强制本地账号登录；密码使用 salted scrypt，访问令牌只以摘要写入 SQLite，会话通过 HttpOnly、SameSite=Strict Cookie 或 Bearer Token 使用。
- `owner`、`admin`、`reviewer`、`viewer` 四类角色；组织边界由登录身份决定，不再信任浏览器自行填写租户请求头。
- 工作台审阅与处置统计、近期审阅、历史搜索、状态筛选、分页、软删除、回收站恢复，以及 HTML/JSON 报告导出。
- 审阅完成后自动生成风险与义务工作项；支持负责人、截止时间、处置备注、事件时间线、乐观锁冲突保护和人工审批状态机。
- 解析 PDF、DOCX、TXT、Markdown；混合模式还支持常见图片及纯扫描 PDF 的 OpenAI Vision OCR。
- 确定性风险规则、本地可追溯知识、原文证据校验、修改建议、义务清单和人工反馈。
- SQLite 版本化迁移、校验备份和安全恢复；应用启动也会幂等升级数据库。
- 统一错误结构、`X-Request-ID`、JSON 请求日志，以及独立 `/live`、`/ready` 探针。
- 上传字节数、PDF 页数、抽取字符数、DOCX 解压体积和 OCR 像素预算。

当前审阅是同步 HTTP 请求：页面会一直等待服务返回结果。项目尚未实现异步任务队列、多副本会话、跨副本 Redis 缓存、Prometheus 指标或自动告警；不要把可选客户端和 Compose profile 当作这些能力已经接入。

## 本地快速开始

要求 Python 3.12。首次安装并启动：

```bash
make install
cp .env.example .env.local
make dev
```

打开：

- 中文工作台：`http://127.0.0.1:8010`
- API 文档：`http://127.0.0.1:8010/docs`
- 存活检查：`http://127.0.0.1:8010/live`
- 就绪检查：`http://127.0.0.1:8010/ready`

`.env.local` 已被 Git 和 Docker 构建上下文忽略。进程环境变量优先于文件内容；不要把模型密钥写入源码、镜像、日志或聊天记录。

### 第一次注册

全新数据库没有用户时，首页会自动显示“创建第一个管理员账号”：

1. 填写组织名称、姓名和邮箱。
2. 设置至少 12 位密码，并在大小写字母、数字、符号四类中至少包含三类。
3. 点击“创建账号并进入”；第一个账号成为组织 `owner`。
4. 以后使用同一邮箱和密码登录。生产环境建议把 `CONTRACT_GUARD_REGISTRATION_ENABLED` 设为 `false`；空数据库仍允许首次 owner 初始化，初始化后不再开放新组织自助注册。

### UI 使用路径

1. **工作台**：查看审阅统计，以及我的未完成、逾期、高风险未关闭、待审批和本周完成数量。
2. **新建审阅**：粘贴合同或上传文件，可填写合同编号；提交后等待真实服务结果，不显示模拟阶段。
3. **处置中心**：按工作类型、状态、负责人和是否逾期筛选工作项；有权限的成员可领取或指派、设置截止时间、更新处置状态并查看变更时间线。
4. **审阅详情**：逐项查看风险等级、原文证据、修改建议、义务与知识来源；风险和义务卡片直接关联处置工作项，并可按角色提交审批、批准或驳回。
5. **审阅记录**：按合同编号或文件名搜索，按状态筛选和翻页；勾选“包含已删除记录”可找到并恢复软删除记录。
6. **账户安全**：查看当前角色并修改密码；修改成功后所有会话失效，需要重新登录。
7. **成员与日志**：owner/admin 可创建成员、调整角色和状态，并查看最近的关键操作记录。

合同原始二进制和抽取后的全文不会落库；文件名、指纹、报告中的必要证据片段、审阅报告及反馈会写入服务端 SQLite。浏览器不使用本地存储保存合同。软删除不是永久销毁，数据库及备份保留期需要由部署方单独管理。

## 运行模式

| 模式 | 配置 | 行为 |
|---|---|---|
| 离线 | `APP_MODE=offline` | 默认模式；只运行本地规则、本地知识和证据校验，不需要模型密钥。 |
| 混合 | `APP_MODE=hybrid` + `OPENAI_API_KEY` | 在本地规则基础上调用 OpenAI 结构化复核；图片和纯扫描 PDF 可使用 Vision OCR。配置 `LIGHTRAG_BASE_URL` 时尝试远程知识检索，失败后回退本地知识。 |

当前配置只接受 `offline` 和 `hybrid`。混合模式缺少 `OPENAI_API_KEY` 时 `/ready` 返回 503；模型调用失败时该次审阅会标记为失败，不会把离线结果伪装成完整 AI 复核。

启用混合模式：

```dotenv
APP_MODE=hybrid
OPENAI_API_KEY=your-key-from-a-secret-manager
OPENAI_MODEL=gpt-5.6-luna
```

保存后重启 `make dev`。响应中的 `report.quality.llm_review_performed` 表示模型复核是否实际完成。

## 账号与权限

| 角色 | 审阅可见范围 | 审阅操作 | 工作项与审批 | 成员与审计 |
|---|---|---|---|---|
| `owner` | 组织内全部审阅 | 新建、反馈、导出、删除/恢复任意记录 | 可指派和更新工作项、接受风险、豁免义务，并提交、批准、驳回或重新打开审批 | 可管理成员并查看审计；owner 不能被降级或禁用 |
| `admin` | 组织内全部审阅 | 新建、反馈、导出、删除/恢复任意记录 | 与 owner 相同的处置和审批权限 | 可管理非 owner 成员并查看审计，不能取得所有权 |
| `reviewer` | 组织内全部审阅 | 新建、反馈、导出；只能删除/恢复本人创建的记录 | 只能领取给自己并更新本人负责的工作项；不能接受风险或豁免义务；只能把草稿或已驳回审阅提交为待审批 | 不可访问 |
| `viewer` | 组织内全部审阅 | 只读查看和导出 | 只读查看工作项、事件和审批状态 | 不可访问 |

这些限制由 API 根据服务端会话强制执行，前端隐藏按钮只是体验辅助。登录失败使用进程内滑动窗口限速；多副本部署前必须替换为共享限速实现。

### 处置与审批状态机

- 风险工作项：`open` 可进入 `in_progress`、`resolved` 或 `accepted`；处理中可退回 `open` 或完成处置；`resolved`、`accepted` 只能重新打开为 `open`。解决或接受风险必须填写处置说明，`accepted` 仅 owner/admin 可用。
- 义务工作项：`pending` 可进入 `in_progress`、`completed` 或 `waived`；处理中可退回 `pending` 或完成处置；`completed`、`waived` 只能重新打开为 `pending`。豁免义务必须填写说明，且仅 owner/admin 可用。
- 审阅审批：`draft -> in_review -> approved|rejected`；`rejected` 可重新提交为 `in_review`，已批准审阅只有 owner/admin 可以重新打开。存在未解决或未接受的 `high`/`critical` 风险时，批准请求返回 `409`。
- 工作项和审阅审批更新都必须携带服务端最近返回的 `expected_version`；版本过期返回 `409`，客户端应刷新后让用户重新确认，不能静默覆盖其他成员的修改。

## API 快速验证

先创建组织 owner，并让 curl 保存 HttpOnly Cookie：

```bash
curl --fail-with-body -c /tmp/contractguard.cookies \
  -X POST http://127.0.0.1:8010/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_name": "演示组织",
    "display_name": "演示管理员",
    "email": "owner@example.com",
    "password": "Replace-Me!2026"
  }'
```

提交文本审阅：

```bash
curl --fail-with-body -b /tmp/contractguard.cookies \
  -X POST http://127.0.0.1:8010/api/v1/reviews/text \
  -H 'Content-Type: application/json' \
  -d '{
    "contract_id": "demo-001",
    "filename": "软件服务合同.txt",
    "text": "任一方未在到期前三十日书面通知终止的，本合同自动续期十二个月。"
  }'
```

主要端点：

| 方法与路径 | 用途 |
|---|---|
| `GET /api/v1/auth/status` | 判断是否需要首次初始化 |
| `POST /api/v1/auth/login`、`POST /api/v1/auth/refresh`、`POST /api/v1/auth/logout` | 会话生命周期 |
| `GET /api/v1/dashboard/summary` | 工作台汇总 |
| `POST /api/v1/reviews/text`、`POST /api/v1/reviews` | 文本或文件审阅 |
| `GET /api/v1/reviews?q=&status=&page=&page_size=` | 搜索、筛选、分页 |
| `GET /api/v1/reviews/{id}` | 审阅详情 |
| `DELETE /api/v1/reviews/{id}`、`POST /api/v1/reviews/{id}/restore` | 软删除与恢复 |
| `GET /api/v1/reviews/{id}/export?format=html|json` | 报告导出 |
| `POST /api/v1/reviews/{id}/feedback` | 人工反馈 |
| `GET /api/v1/operations/summary` | 我的待办、逾期、高风险未关闭、待审批和本周完成汇总 |
| `GET /api/v1/work-items?kind=&status=&assignee=&overdue=&risk_level=` | 工作项筛选与分页；`assignee` 可用 `me` 或 `unassigned` |
| `GET /api/v1/reviews/{id}/work-items` | 查看某次审阅生成的风险与义务工作项 |
| `GET /api/v1/work-items/{id}`、`GET /api/v1/work-items/{id}/events` | 工作项详情与变更时间线 |
| `PATCH /api/v1/work-items/{id}` | 携带 `expected_version` 更新负责人、截止时间、备注或处置状态 |
| `PATCH /api/v1/reviews/{id}/decision` | 携带 `expected_version` 流转审阅审批状态 |
| `GET/POST/PATCH /api/v1/users` | owner/admin 成员管理 |
| `GET /api/v1/audit-logs` | owner/admin 审计查询 |

认证 API 也会返回 Bearer Token，适合非浏览器客户端。错误响应统一包含 `success=false`、`code`、`message`、兼容字段 `detail` 和 `requestId`；同一请求 ID 也位于 `X-Request-ID` 响应头。

## 配置

完整模板见 [`.env.example`](.env.example)。常用变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_MODE` | `offline` | `offline` 或 `hybrid` |
| `OPENAI_API_KEY` | 空 | 混合模式必需 |
| `OPENAI_MODEL` | `gpt-5.6-luna` | Responses API 与 Vision 使用的模型 |
| `DATABASE_URL` | `sqlite:///./data/contractguard.db` | 内建仓储只支持 SQLite URL |
| `CONTRACT_GUARD_AUTH_REQUIRED` | `true` | 是否强制登录；生产环境不要关闭 |
| `CONTRACT_GUARD_REGISTRATION_ENABLED` | `true` | 是否允许额外组织自助注册 |
| `CONTRACT_GUARD_AUTH_COOKIE_SECURE` | `false` | HTTPS 部署必须设为 `true` |
| `CONTRACT_GUARD_LOGIN_ATTEMPT_LIMIT` | `10` | 登录窗口内失败次数上限 |
| `CONTRACT_GUARD_LOGIN_WINDOW_SECONDS` | `300` | 登录限速窗口 |
| `CONTRACT_GUARD_LEGACY_TENANT_HEADERS_ENABLED` | `false` | 仅旧版自动化测试兼容；共享服务禁止开启 |
| `CONTRACT_GUARD_MAX_UPLOAD_BYTES` | `20971520` | 整体上传上限，默认 20 MiB |
| `CONTRACT_GUARD_MAX_DOCUMENT_PAGES` | `200` | PDF 最大页数 |
| `CONTRACT_GUARD_MAX_DOCUMENT_CHARACTERS` | `1000000` | 抽取文本最大字符数 |
| `CONTRACT_GUARD_MAX_DOCX_UNCOMPRESSED_BYTES` | `104857600` | DOCX 解压预算 |
| `CONTRACT_GUARD_MAX_OCR_PIXELS` | `20000000` | 单张 OCR 图像像素预算 |
| `CONTRACT_GUARD_DOCS_ENABLED` | `true` | 是否暴露 `/docs` 和 `/redoc` |
| `LOG_LEVEL` | `info` | 应用与 Uvicorn 日志级别 |

`/live` 只表示进程能响应；`/ready` 检查 SQLite 以及混合模式所需密钥是否配置，不会向 OpenAI 或 LightRAG 发起真实网络探测。`/health` 提供 UI 所需的服务能力信息。

## 数据库迁移、备份和恢复

```bash
make db-status
make db-backup BACKUP=backups/pre-release.db
make db-upgrade
make db-restore BACKUP=backups/pre-release.db
```

`db-restore` 前必须停止应用。恢复工具不会静默覆盖既有状态：它会先创建 pre-restore 安全快照，再校验并原子替换。完整操作手册见 [`docs/MIGRATIONS.md`](docs/MIGRATIONS.md)。

当前最新结构为 V3 `operational_work_items`。V3 新增工作项与事件表，并为升级前已经完成的审阅按报告顺序幂等回填风险和义务工作项。数据库备份会同时包含工作项、处置备注、事件、负责人、截止时间和审批状态；恢复到发布前备份也会回退备份点之后的这些业务操作，因此回滚前必须另存当前故障现场。

## 容器与部署

```bash
docker compose up --build
```

Compose 默认映射到 `http://127.0.0.1:8010` 并使用 SQLite 命名卷。Kubernetes 单副本清单、HTTPS Cookie、探针、迁移 init container 和生产边界见 [`deploy/README.md`](deploy/README.md)。

当前内建实现只支持单实例 SQLite。请勿仅通过启动 Redis、Kafka、MySQL、Neo4j 或 Milvus 容器就提高副本数；应用尚未把这些服务接入默认运行路径。

## 质量检查

```bash
make check
make build
```

`make check` 执行 Ruff lint、Mypy 类型检查、格式检查、Pytest 和浏览器 JavaScript 语法检查。CI 还会在干净的 Python 3.12 环境构建 wheel、验证 UI 与离线知识资源确实打包，并在 Docker 可用的 runner 上构建镜像。

## 安全与隐私边界

- 合同可能包含商业秘密与个人信息；只上传有权处理且符合最小必要原则的内容。
- 报告证据片段、报告、反馈、审计和软删除状态会保存在 SQLite；必须对数据库、PVC 和备份实施加密、访问控制、保留和销毁策略。
- 上传文件、文件名、合同文本和检索内容均是不可信输入；当前资源预算不能替代恶意文件扫描。
- 模型输出不能覆盖确定性证据校验，引用必须对应真实条款或检索片段。
- 普通请求日志不应记录合同全文、密码、令牌或密钥；排障时使用 `requestId` 关联日志。
- 生产环境必须使用 HTTPS、Secure Cookie 和受管密钥，并完成备份恢复、权限越权、模型故障与日志告警演练。
