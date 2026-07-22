# ContractGuard 大规模重构交付报告

日期：2026-07-18  
交付状态：可安装、可构建、可启动、可登录、可完成核心合同审阅闭环。

## 1. 重构目标与产品定位

ContractGuard 不再是菜品推荐或单页演示，而是一套面向法务、采购和业务审阅人的合同预审工作台。它解决的核心问题是：在不丢失合同原文证据的前提下，快速定位高风险条款、整理履约义务，并让结果能够被检索、反馈、导出和审计。

用户最常执行的三个操作：

1. 粘贴或上传合同并发起审阅；
2. 核对风险、原文证据、修改建议和义务；
3. 在工作台和历史列表中搜索、导出、删除或恢复记录。

系统仍是辅助预审工具，不构成法律意见。默认离线模式使用确定性规则和合成知识库；混合模式才调用 OpenAI。

## 2. 重构前后对比

| 维度 | 重构前 | 重构后 |
|---|---|---|
| 架构 | API、租户头、审阅流程和单页 UI 耦合；路由文件承担过多职责 | 身份、工作区、审阅、迁移、文档解析、缓存和 Agent 工作流分层；依赖可替换 |
| 功能 | 只能即时提交并看一次结果，缺少登录、历史管理和工作台 | 登录、工作台、历史搜索筛选分页、详情、反馈、导出、软删除恢复、成员与审计闭环 |
| 数据库 | 应用启动时直接建表，无版本、备份和回滚流程 | SQLite V1/V2 版本迁移、校验、备份、安全恢复和启动前幂等升级 |
| 权限 | 浏览器可伪造 `X-Org-ID` / `X-Session-ID`；无真实账号和角色 | 服务端会话派生组织；owner/admin/reviewer/viewer 后端 RBAC；旧租户头默认禁用 |
| 体验 | 页面更像落地页，处理状态为模拟文案，入口和数据保存边界不清楚 | 工作台式导航、真实等待状态、空/错/成功状态、二次确认、账户和成员页、375px 响应式 |
| 安全 | 无密码策略、会话轮换、限速、请求关联、资源预算 | salted scrypt、摘要令牌、刷新轮换、防重放、登录限速、请求 ID、统一错误、上传复杂度预算 |
| 测试 | 58 项测试，缺少认证、迁移、分发和生命周期覆盖 | 78 项测试；增加认证/RBAC、迁移/恢复、历史、删除恢复、资源预算和 wheel 资源测试 |
| 部署 | wheel 构建环境不完整，探针和运行边界不清 | wheel 可构建，CI、Dockerfile、Compose、Kubernetes 单副本清单、`/live`、`/ready` 和部署手册 |

## 3. 目标架构

```text
浏览器 / API 客户端
  -> FastAPI 请求 ID、错误处理、Cookie/Bearer 认证
  -> identity / workspace / reviews 路由
  -> 文档解析、缓存、事件、知识、记忆、审计服务
  -> LangGraph 合同审阅工作流
       -> 确定性规则
       -> 本地知识 / 可选 LightRAG
       -> 可选 OpenAI 结构化复核和 Vision OCR
       -> 原文证据校验与质量指标
  -> SQLite 仓储与版本迁移
```

主要职责：

- `api/auth_routes.py`：注册、登录、刷新、退出、改密、成员和审计 API；
- `api/workspace_routes.py`：工作台、历史列表、搜索分页、删除恢复和导出；
- `api/routes.py`：合同审阅、反馈、义务和记忆 API；
- `services/identity.py`：本地身份、会话、RBAC、密码与审计；
- `services/documents.py`：PDF、DOCX、文本、图片解析和资源预算；
- `agent/workflow.py`：证据优先的 Agent 工作流；
- `infrastructure/db/migrations.py`：版本化迁移、备份和恢复；
- `web/`：无构建步骤的响应式工作台 UI。

## 4. 角色与权限矩阵

| 功能 | owner | admin | reviewer | viewer |
|---|---:|---:|---:|---:|
| 查看组织内审阅 | 是 | 是 | 是 | 是 |
| 新建审阅、提交反馈 | 是 | 是 | 是 | 否 |
| 导出报告 | 是 | 是 | 是 | 是 |
| 删除/恢复本人记录 | 是 | 是 | 是 | 否 |
| 删除/恢复他人记录 | 是 | 是 | 否 | 否 |
| 创建和管理成员 | 是 | 是（不能取得或修改 owner 所有权） | 否 | 否 |
| 查看审计日志 | 是 | 是 | 否 | 否 |
| 修改本人密码 | 是 | 是 | 是 | 是 |

所有权限都在 API 层再次验证，不依赖前端传入角色。`CONTRACT_GUARD_AUTH_REQUIRED=false` 只用于单机兼容；此时客户端租户头仍默认关闭。身份管理和审计接口即使在兼容模式也必须真实登录。

## 5. 已完成模块

### 5.1 身份与权限

- 首个 owner 初始化、注册开关、登录、退出、访问令牌和刷新令牌；
- HttpOnly、SameSite=Strict Cookie，同时支持 Bearer Token；
- 密码不少于 12 位，四类字符至少满足三类；
- salted scrypt 密码摘要，令牌仅持久化 SHA-256 摘要；
- 刷新令牌原子轮换，旧访问/刷新令牌失效；
- 进程内登录滑动窗口限速；
- owner 保护、管理员禁止自升 owner、禁用账号立即撤销会话；
- 成员创建、角色/状态修改和改密后全会话撤销。

### 5.2 核心审阅 Agent

- 保留证据优先 LangGraph 流程、确定性规则、知识检索和记忆上下文；
- 支持离线和混合两种真实运行模式；
- 风险必须包含合同原文证据；
- 生成风险等级、描述、建议、义务、质量指标和免责声明；
- 人工反馈真实写入数据库并进入审计；
- 工作流异常对客户端返回安全错误，内部日志使用 request ID 关联。

### 5.3 文档处理

- PDF、DOCX、TXT、Markdown；混合模式支持图片和扫描 PDF OCR；
- 安全文件名、MIME/签名识别和二进制文本拒绝；
- 20 MiB 上传、200 页、100 万字符、100 MiB DOCX 解压、2000 万 OCR 像素默认预算；
- PNG/JPEG/GIF/BMP/WebP/TIFF 尺寸在解码前尽量校验；
- 原始文件和抽取全文不落库，只保存文件名、指纹、必要证据片段、报告和反馈。

### 5.4 工作区与数据管理

- 数据库真实统计的工作台和最近审阅；
- 关键词搜索、状态筛选、排序、分页和无结果状态；
- 审阅详情、HTML/JSON 导出、软删除、回收站和恢复；
- 关键危险操作二次确认；
- owner/admin 成员管理与最近 50 条审计日志；
- 请求 ID、统一错误结构和 JSON 访问日志。

### 5.5 UI/UX

- 登录、首次设置、工作台、历史、新建、详情、账户、成员与日志页面；
- 根据服务端角色隐藏无权入口，但后端仍独立鉴权；
- 不再显示模拟分析阶段；
- 明确数据保存、离线/AI 状态和法律边界；
- 加载、错误、成功、空数据、无搜索结果和会话失效状态；
- 桌面侧栏、手机顶部栏和底部导航；375px 无横向溢出，交互控件高度不低于 44px；
- 无 `localStorage` 合同持久化，无客户端租户头。

### 5.6 工程和部署

- Ruff、Mypy、Pytest、JavaScript 语法和 wheel 构建进入统一质量门禁；
- GitHub Actions 执行质量、资源打包和 Docker 镜像构建；
- 非 root Docker 镜像、Compose 单实例 SQLite 运行；
- Kubernetes 单副本、迁移 init container、PVC、安全上下文和探针；
- `/live` 仅检查进程，`/ready` 检查数据库和必需配置。

## 6. 新增实用功能

| 功能 | 使用角色 | 使用场景 | 用户价值 |
|---|---|---|---|
| 首次 owner 初始化和登录 | 所有人/owner | 全新部署首次进入 | 不再依赖伪租户头，建立真实数据边界 |
| 组织成员与角色 | owner/admin | 邀请法务、业务和只读同事 | 最小权限协作，禁用即时生效 |
| 工作台 | 全部登录用户 | 每日进入系统 | 一眼看到总量、高风险、失败和最近记录 |
| 历史搜索筛选分页 | 全部登录用户 | 找到过去合同 | 从一次性演示变成可持续工作区 |
| 软删除与恢复 | owner/admin/reviewer | 清理误建或过期记录 | 避免误操作直接丢失结果 |
| HTML/JSON 导出 | 全部登录用户 | 交接、归档或二次处理 | 结果可带出系统并保持证据关系 |
| 风险反馈 | owner/admin/reviewer | 人工复核 AI/规则结果 | 记录有帮助或需复核信号 |
| 改密与会话撤销 | 全部登录用户 | 密码轮换 | 旧会话和旧密码立即失效 |
| 审计日志 | owner/admin | 排障和权限审查 | 可追踪谁在何时操作了什么对象 |
| 资源预算 | 系统 | 处理恶意或异常大文件 | 限制压缩膨胀、页数、字符和 OCR 成本 |

## 7. 删除或替换内容

- 替换旧的落地页式单屏 UI，保留核心风险展示但改成工作台信息架构；
- 删除模拟进度阶段，改为真实等待、超时提示和历史回看；
- 删除浏览器 `localStorage` 合同数据和客户端租户头依赖；
- 将未认证租户头兼容改为显式、默认关闭的测试开关；
- 将应用内隐式建表替换为独立版本迁移；
- 将原始异常文本返回替换为稳定错误代码、公共消息和 request ID；
- 清理会让人误以为 Redis/Kafka/MySQL/Neo4j/Milvus 已接入默认路径的配置声明；这些仅保留为实验 profile 或可选客户端，不宣称生产集成。

旧审阅数据没有删除。首个 owner 会认领唯一的旧组织，从而继续查看迁移前记录。

## 8. 数据库迁移与回滚

### 8.1 执行顺序

1. 停止写入；
2. `make db-status`；
3. `make db-backup BACKUP=backups/pre-upgrade.db`；
4. `make db-upgrade`；
5. 启动服务并检查 `/ready`；
6. 完成注册、登录、列表、审阅、删除恢复和审计冒烟。

### 8.2 迁移内容

- V1：`reviews`、`review_feedback`、`memories` 基线及索引；
- V2：`organizations`、`users`、`auth_sessions`、`audit_logs`、`finding_actions`；
- V2 为 `reviews` 增加 `created_by_user_id`、`deleted_at`、`decision_status`、`state_version`、`analysis_version` 和 `idempotency_key`；
- 迁移只做增量创建和加列，不重写旧审阅内容。

当前真实数据库：schema V2，4 条审阅、4 条记忆、1 个待认领旧组织、0 个用户。迁移前后数据计数一致。

已验证备份：

- 文件：`data/backups/contractguard-v2-verified-20260717.db`
- SHA-256：`ad88efca2779b13b11d94197993477d0347f3b120c81fb8e9d1702f7474a768e`
- 大小：180224 字节

### 8.3 回滚

不提供破坏性的 down migration。回滚通过经过校验的整库恢复完成：

```bash
make db-restore BACKUP=data/backups/contractguard-v2-verified-20260717.db
```

恢复前必须停止应用。工具会先创建 pre-restore 安全快照，再校验来源并原子替换目标。完整说明见 `docs/MIGRATIONS.md`。

## 9. 接口变化

新增或完善的主要端点：

| 方法 | 路径 | 权限/作用 |
|---|---|---|
| GET | `/api/v1/auth/status` | 首次初始化状态 |
| POST | `/api/v1/auth/register` | 首个 owner 或开放注册 |
| POST | `/api/v1/auth/login` | 登录和设置会话 Cookie |
| POST | `/api/v1/auth/refresh` | 原子轮换会话 |
| POST | `/api/v1/auth/logout` | 撤销当前会话 |
| GET | `/api/v1/auth/me` | 当前身份 |
| POST | `/api/v1/auth/change-password` | 改密并撤销全部会话 |
| GET/POST | `/api/v1/users` | owner/admin 查询或创建成员 |
| PATCH | `/api/v1/users/{user_id}` | owner/admin 修改角色或状态 |
| GET | `/api/v1/audit-logs` | owner/admin 审计分页 |
| GET | `/api/v1/dashboard/summary` | 真实工作台统计 |
| GET | `/api/v1/reviews` | 搜索、筛选、排序和分页 |
| POST | `/api/v1/reviews/text` | 文本合同审阅 |
| POST | `/api/v1/reviews` | 文件合同审阅 |
| GET | `/api/v1/reviews/{id}` | 审阅详情 |
| POST | `/api/v1/reviews/{id}/feedback` | 风险反馈 |
| DELETE | `/api/v1/reviews/{id}` | 软删除 |
| POST | `/api/v1/reviews/{id}/restore` | 恢复 |
| GET | `/api/v1/reviews/{id}/export` | HTML/JSON 导出 |
| GET | `/live`、`/ready`、`/health` | 存活、就绪、UI 能力信息 |

错误统一为 `success=false`、`code`、`message`、`detail`、`requestId`，并通过 `X-Request-ID` 响应头关联服务端日志。

## 10. 环境变量

完整、无真实密钥的模板位于项目根目录 `.env.example`，覆盖：

- `APP_MODE=offline|hybrid`；
- OpenAI 模型、超时、重试和可选 LightRAG；
- SQLite 路径；
- 认证开关、注册开关、Cookie、会话 TTL、登录限速；
- 上传、页数、字符、DOCX 解压和 OCR 像素预算；
- CORS、API 前缀、文档和日志；
- 默认关闭的旧租户头兼容开关。

`.env.local` 被 Git 和 Docker 忽略，进程环境变量优先。生产密钥必须来自密钥管理服务，不得提交到源码、日志、镜像或文档。

## 11. 启动与部署

### 11.1 本地开发

```bash
make install
cp .env.example .env.local
make db-upgrade
make dev
```

访问 `http://127.0.0.1:8010`，首次创建 owner 后即可使用。当前交付已在本机启动该地址。

### 11.2 启用 OpenAI 混合复核

```dotenv
APP_MODE=hybrid
OPENAI_API_KEY=从密钥管理器注入
```

重启服务后检查 `/ready`。默认离线模式不会调用 OpenAI，也不会产生模型费用。

### 11.3 质量和构建

```bash
make check
make build
```

生成的 wheel：`dist/contractguard-0.1.0-py3-none-any.whl`，大小 122668 字节，SHA-256：`c60a8f640988b6905f32a93c521d1f4a8a04d785dd0b4e24f4f6e44471958778`。

### 11.4 容器

```bash
docker compose up --build
```

当前内建数据和会话实现只支持单实例 SQLite。Kubernetes 清单也固定单副本；横向扩容前必须迁移共享数据库、会话、缓存和限速。

## 12. 验证结果

| 验证 | 命令/方式 | 结果 |
|---|---|---|
| Python lint | `python -m ruff check src tests` | 通过 |
| Python 类型 | `python -m mypy src` | 32 个源文件，无问题 |
| Python 格式 | `python -m ruff format --check src tests` | 45 个文件通过 |
| 自动测试 | `python -m pytest` | 78 passed，6 个第三方弃用警告 |
| 前端语法 | `node --check src/contract_guard/web/app.js` | 通过 |
| wheel 构建 | `make build` | 成功，包含 UI 和离线知识库 |
| wheel 独立资源 | 临时解压后从项目目录外读取默认知识库 | 通过 |
| 迁移状态 | `make db-status` | schema V2，pending 为空 |
| 备份 | SQLite backup + SHA-256 + schema 校验 | 通过 |
| 服务启动 | `make dev`、`/live`、`/ready`、`/health` | 通过 |
| 浏览器桌面流程 | 注册→审阅→证据→反馈→搜索→删除→恢复→成员→审计→只读登录 | 通过 |
| 浏览器手机流程 | 375×812 视口、导航、横向溢出和 44px 控件检查 | 通过；无控制台错误 |
| Docker 本机实构 | `docker build` | 本机未安装 Docker，未执行；CI 已配置 Docker runner 实构 |

浏览器验收使用独立的 `/tmp` 离线数据库，不读取真实密钥、不调用 OpenAI、不污染正式数据库。

## 13. 兼容性影响

- 默认现在必须登录；旧客户端直接传 `X-Org-ID` 会收到 401 或被锁定到服务器默认组织；
- 如需运行旧自动化测试，必须同时显式设置 `AUTH_REQUIRED=false` 和危险兼容开关；共享或公网服务禁止这样配置；
- 旧审阅数据通过 V2 加列兼容，没有被重写；
- 首个 owner 会认领唯一无用户旧组织；若存在多个无用户组织，需要人工制定归属后再开放初始化；
- API v1 的审阅提交和详情主体结构保持兼容，只增加身份和生命周期字段；
- UI 不再使用浏览器本地存储保存合同。

## 14. 剩余问题与后续建议

| 优先级 | 问题 | 原因/影响 | 建议 |
|---|---|---|---|
| P1 | 审阅仍是同步 HTTP 请求 | 长合同会占用请求，浏览器超时后只能去历史查看 | 增加持久化 job、worker、真实阶段事件和可恢复状态机 |
| P1 | 单实例 SQLite、内存缓存和本地限速 | 不能安全横向扩容 | 迁移 PostgreSQL、共享 Redis 会话/缓存/限速，并做并发压测 |
| P1 | 只有软删除，没有保留期自动清理或永久销毁 API | 敏感证据仍在数据库和备份 | 制定保留策略，增加 owner 永久删除和备份销毁流程 |
| P1 | 未集成恶意文件扫描 | 资源预算只能控制复杂度，不能识别病毒 | 上传入口接入隔离扫描服务和内容安全策略 |
| P2 | 本地账号没有找回密码、MFA、SSO 和设备管理 | 企业身份治理能力有限 | 接入受管 IdP，保留当前接口作为开发模式 |
| P2 | 没有指标、追踪和自动告警 | 目前只有结构化日志和探针 | 增加 OpenTelemetry、Prometheus 指标、SLO 和告警演练 |
| P2 | 本地知识为明确标注的合成演示政策 | 不能替代真实法务知识 | 建立知识审批、版本、管辖区、有效期和撤回流程 |
| P2 | HTML 导出为同步单条报告 | 当前数据量足够，大批量导出不适用 | 后续与异步 job 一起实现筛选导出和下载过期 |
| P3 | 第三方测试仍有 Starlette/httpx2 和 PyMuPDF SWIG 弃用警告 | 不影响当前功能，升级后可能变化 | 在依赖升级窗口验证 FastAPI/Starlette 与 httpx2 兼容性 |
| P3 | 当前目录不是 Git 仓库 | 无法创建真实分支或提交记录 | 接入版本控制后按模块拆分提交并保护主分支 |

以上剩余项已明确披露，不会把未接入的 Redis、Kafka、Prometheus 或异步队列描述为现有能力。
