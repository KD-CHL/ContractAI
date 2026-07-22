"use strict";

const DEFAULT_MAX_FILE_BYTES = 20 * 1024 * 1024;
const REVIEW_TIMEOUT_MS = 180_000;
const PAGE_SIZE = 10;
const WORK_PAGE_SIZE = 20;

const SAMPLE_CONTRACT = `软件服务合同（演示）

第一条 服务期限
本合同有效期为十二个月。任一方未在到期前三十日书面通知终止的，本合同自动续期十二个月。

第二条 验收与付款
甲方应在收到交付成果后五个工作日内完成验收。期限内未提出书面异议的，视为验收合格。甲方必须在验收合格后十日内支付全部费用。

第三条 责任
因履行本合同产生的全部损失均由乙方承担，乙方承担无限责任。

第四条 合同变更
甲方有权根据业务需要随时单方修改服务内容及费用标准。`;

const RISK_LABELS = {
  critical: "严重风险",
  high: "高风险",
  medium: "中风险",
  low: "低风险",
  info: "提示",
};

const RISK_ORDER = { critical: 5, high: 4, medium: 3, low: 2, info: 1 };
const STATUS_LABELS = {
  processing: "处理中",
  completed: "已完成",
  failed: "失败",
};

const WORK_KIND_LABELS = {
  finding: "风险处置",
  obligation: "合同义务",
};

const WORK_STATUS_LABELS = {
  open: "待处理",
  pending: "待履行",
  in_progress: "处理中",
  resolved: "已解决",
  accepted: "已接受风险",
  completed: "已完成",
  waived: "已豁免",
};

const WORK_STATUS_OPTIONS = {
  finding: ["open", "in_progress", "resolved", "accepted"],
  obligation: ["pending", "in_progress", "completed", "waived"],
};

const WORK_TRANSITIONS = {
  finding: {
    open: ["in_progress", "resolved", "accepted"],
    in_progress: ["open", "resolved", "accepted"],
    resolved: ["open"],
    accepted: ["open"],
  },
  obligation: {
    pending: ["in_progress", "completed", "waived"],
    in_progress: ["pending", "completed", "waived"],
    completed: ["pending"],
    waived: ["pending"],
  },
};

const TERMINAL_WORK_STATUSES = new Set(["resolved", "accepted", "completed", "waived"]);

const DECISION_LABELS = {
  draft: "草稿",
  in_review: "审批中",
  approved: "已批准",
  rejected: "已驳回",
};

const DECISION_DESCRIPTIONS = {
  draft: "审阅结果仍在处置阶段。完成关键风险处置后，可提交团队复核。",
  in_review: "这份审阅正在等待审批。高风险工作项未关闭时，批准操作可能被阻止。",
  approved: "审阅决定已批准。后续变更需要重新提交复核并保留审计记录。",
  rejected: "审阅决定已驳回。请结合审批说明继续处理后，再重新提交复核。",
};

const DECISION_TRANSITIONS = {
  draft: ["in_review"],
  in_review: ["approved", "rejected"],
  approved: ["in_review"],
  rejected: ["in_review"],
};

const ROLE_LABELS = {
  owner: "组织所有者",
  admin: "管理员",
  reviewer: "审阅人",
  viewer: "只读成员",
};

const USER_STATUS_LABELS = {
  active: "正常",
  disabled: "已禁用",
};

const ROLE_DESCRIPTIONS = {
  owner: "可管理成员，并查看、删除或恢复全部审阅记录。",
  admin: "可管理成员，并查看、删除或恢复全部审阅记录。",
  reviewer: "可新建审阅和提交反馈，只能删除或恢复自己创建的记录。",
  viewer: "可查看和导出组织记录，不能新建审阅、提交反馈或删除记录。",
};

const AUDIT_ACTION_LABELS = {
  "identity.organization_registered": "创建组织和所有者账号",
  "identity.login": "登录账户",
  "identity.logout": "退出账户",
  "identity.password_changed": "修改密码",
  "identity.member_created": "创建组织成员",
  "identity.member_updated": "更新成员权限或状态",
  "review.created": "创建合同审阅",
  "review.completed": "完成合同审阅",
  "review.failed": "合同审阅失败",
  "review.deleted": "删除审阅记录",
  "review.restored": "恢复审阅记录",
  "review.exported": "导出审阅报告",
  "review.feedback_submitted": "提交风险反馈",
  "review.decision_changed": "更新审阅决定",
  "work_item.updated": "更新处置工作项",
};

const WARNING_TRANSLATIONS = {
  "LLM analysis was skipped; results are rule-based only.":
    "本次未调用 AI，结果来自本地规则与知识库。",
  "No evidence-backed risk finding was produced.":
    "本次没有生成具备合同原文证据的风险提示。",
  "LLM review was not requested; deterministic rules still ran.":
    "本次未请求 AI，确定性规则仍已完成审阅。",
};

class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

const elements = {
  authView: document.querySelector("#auth-view"),
  appView: document.querySelector("#app-view"),
  authServiceState: document.querySelector("#auth-service-state"),
  authServiceText: document.querySelector("#auth-service-text"),
  authLoading: document.querySelector("#auth-loading"),
  authContent: document.querySelector("#auth-content"),
  authEyebrow: document.querySelector("#auth-eyebrow"),
  authTitle: document.querySelector("#auth-title"),
  authDescription: document.querySelector("#auth-description"),
  authError: document.querySelector("#auth-error"),
  loginForm: document.querySelector("#login-form"),
  registerForm: document.querySelector("#register-form"),
  authSwitch: document.querySelector("#auth-switch"),
  sidebarUserName: document.querySelector("#sidebar-user-name"),
  sidebarUserEmail: document.querySelector("#sidebar-user-email"),
  userAvatar: document.querySelector("#user-avatar"),
  logoutButton: document.querySelector("#logout-button"),
  mobileLogoutButton: document.querySelector("#mobile-logout-button"),
  adminOnly: [...document.querySelectorAll("[data-admin-only]")],
  reviewCreateOnly: [...document.querySelectorAll("[data-review-create]")],
  workspace: document.querySelector("#main-content"),
  views: [...document.querySelectorAll("[data-view]")],
  routeLinks: [...document.querySelectorAll("[data-route-link]")],
  dashboardLoading: document.querySelector("#dashboard-loading"),
  dashboardError: document.querySelector("#dashboard-error"),
  dashboardContent: document.querySelector("#dashboard-content"),
  reviewSummaryContent: document.querySelector("#review-summary-content"),
  dashboardWelcome: document.querySelector("#dashboard-welcome"),
  metricTotal: document.querySelector("#metric-total"),
  metricCompleted: document.querySelector("#metric-completed"),
  metricHighRisk: document.querySelector("#metric-high-risk"),
  metricFailed: document.querySelector("#metric-failed"),
  recentReviewList: document.querySelector("#recent-review-list"),
  operationsSummaryLoading: document.querySelector("#operations-summary-loading"),
  operationsSummaryError: document.querySelector("#operations-summary-error"),
  operationsSummaryContent: document.querySelector("#operations-summary-content"),
  operationMyOpen: document.querySelector("#operation-my-open"),
  operationOverdue: document.querySelector("#operation-overdue"),
  operationHighRiskOpen: document.querySelector("#operation-high-risk-open"),
  operationPendingApprovals: document.querySelector("#operation-pending-approvals"),
  operationCompletedWeek: document.querySelector("#operation-completed-week"),
  workFilterForm: document.querySelector("#work-filter-form"),
  workKind: document.querySelector("#work-kind"),
  workStatus: document.querySelector("#work-status"),
  workAssignee: document.querySelector("#work-assignee"),
  workOverdue: document.querySelector("#work-overdue"),
  clearWorkFilters: document.querySelector("#clear-work-filters"),
  workError: document.querySelector("#work-error"),
  workLoading: document.querySelector("#work-loading"),
  workResultSummary: document.querySelector("#work-result-summary"),
  workItemList: document.querySelector("#work-item-list"),
  workPagination: document.querySelector("#work-pagination"),
  workPreviousPage: document.querySelector("#work-previous-page"),
  workNextPage: document.querySelector("#work-next-page"),
  workPageStatus: document.querySelector("#work-page-status"),
  reviewFilterForm: document.querySelector("#review-filter-form"),
  reviewSearch: document.querySelector("#review-search"),
  reviewStatus: document.querySelector("#review-status"),
  includeDeleted: document.querySelector("#include-deleted"),
  clearReviewFilters: document.querySelector("#clear-review-filters"),
  reviewsLoading: document.querySelector("#reviews-loading"),
  reviewsError: document.querySelector("#reviews-error"),
  reviewList: document.querySelector("#review-list"),
  reviewPagination: document.querySelector("#review-pagination"),
  previousPage: document.querySelector("#previous-page"),
  nextPage: document.querySelector("#next-page"),
  pageStatus: document.querySelector("#page-status"),
  tabs: [...document.querySelectorAll(".input-tab")],
  textPanel: document.querySelector("#text-panel"),
  filePanel: document.querySelector("#file-panel"),
  contractText: document.querySelector("#contract-text"),
  characterCount: document.querySelector("#character-count"),
  contractFile: document.querySelector("#contract-file"),
  chooseFileButton: document.querySelector("#choose-file-button"),
  dropZone: document.querySelector("#drop-zone"),
  selectedFile: document.querySelector("#selected-file"),
  selectedFileName: document.querySelector("#selected-file-name"),
  selectedFileSize: document.querySelector("#selected-file-size"),
  fileLimitLabel: document.querySelector("#file-limit-label"),
  removeFileButton: document.querySelector("#remove-file-button"),
  contractId: document.querySelector("#contract-id"),
  sampleButton: document.querySelector("#sample-button"),
  reviewButton: document.querySelector("#review-button"),
  reviewError: document.querySelector("#review-error"),
  reviewWait: document.querySelector("#review-wait"),
  accountName: document.querySelector("#account-name"),
  accountEmail: document.querySelector("#account-email"),
  accountOrganization: document.querySelector("#account-organization"),
  accountRole: document.querySelector("#account-role"),
  accountRoleDescription: document.querySelector("#account-role-description"),
  accountStatus: document.querySelector("#account-status"),
  changePasswordForm: document.querySelector("#change-password-form"),
  passwordError: document.querySelector("#password-error"),
  passwordSuccess: document.querySelector("#password-success"),
  adminAccessError: document.querySelector("#admin-access-error"),
  adminContent: document.querySelector("#admin-content"),
  memberCreateForm: document.querySelector("#member-create-form"),
  memberCreateError: document.querySelector("#member-create-error"),
  memberCreateSuccess: document.querySelector("#member-create-success"),
  membersError: document.querySelector("#members-error"),
  membersLoading: document.querySelector("#members-loading"),
  memberList: document.querySelector("#member-list"),
  refreshMembers: document.querySelector("#refresh-members"),
  auditError: document.querySelector("#audit-error"),
  auditLoading: document.querySelector("#audit-loading"),
  auditList: document.querySelector("#audit-list"),
  refreshAudit: document.querySelector("#refresh-audit"),
  detailLoading: document.querySelector("#detail-loading"),
  detailError: document.querySelector("#detail-error"),
  detailContent: document.querySelector("#detail-content"),
  detailStatus: document.querySelector("#detail-status"),
  detailDecisionStatus: document.querySelector("#detail-decision-status"),
  detailDeletedBadge: document.querySelector("#detail-deleted-badge"),
  detailTitle: document.querySelector("#detail-title"),
  detailMeta: document.querySelector("#detail-meta"),
  exportButton: document.querySelector("#export-button"),
  deleteReviewButton: document.querySelector("#delete-review-button"),
  restoreReviewButton: document.querySelector("#restore-review-button"),
  modeNotice: document.querySelector("#mode-notice"),
  approvalStatus: document.querySelector("#approval-status"),
  approvalDescription: document.querySelector("#approval-description"),
  decisionError: document.querySelector("#decision-error"),
  decisionSuccess: document.querySelector("#decision-success"),
  decisionForm: document.querySelector("#decision-form"),
  decisionTarget: document.querySelector("#decision-target"),
  decisionNote: document.querySelector("#decision-note"),
  decisionSubmit: document.querySelector("#decision-submit"),
  decisionReadOnly: document.querySelector("#decision-read-only"),
  summaryFindings: document.querySelector("#summary-findings"),
  summaryHighest: document.querySelector("#summary-highest"),
  summaryHighRisk: document.querySelector("#summary-high-risk"),
  summaryObligations: document.querySelector("#summary-obligations"),
  summaryCoverage: document.querySelector("#summary-coverage"),
  riskFilters: document.querySelector("#risk-filters"),
  riskResultStatus: document.querySelector("#risk-result-status"),
  findingList: document.querySelector("#finding-list"),
  findingsWorkSummary: document.querySelector("#findings-work-summary"),
  obligationList: document.querySelector("#obligation-list"),
  obligationsWorkSummary: document.querySelector("#obligations-work-summary"),
  detailWorkError: document.querySelector("#detail-work-error"),
  contextDrawer: document.querySelector("#context-drawer"),
  contextCount: document.querySelector("#context-count"),
  contextList: document.querySelector("#context-list"),
  qualityPanel: document.querySelector("#quality-panel"),
  legalNotice: document.querySelector("#legal-notice"),
  toastRegion: document.querySelector("#toast-region"),
  confirmDialog: document.querySelector("#confirm-dialog"),
  confirmTitle: document.querySelector("#confirm-title"),
  confirmMessage: document.querySelector("#confirm-message"),
  confirmAction: document.querySelector("#confirm-action"),
  workItemDialog: document.querySelector("#work-item-dialog"),
  workItemForm: document.querySelector("#work-item-form"),
  workItemDialogKind: document.querySelector("#work-item-dialog-kind"),
  workItemDialogTitle: document.querySelector("#work-item-dialog-title"),
  workItemDialogContext: document.querySelector("#work-item-dialog-context"),
  workItemClose: document.querySelector("#work-item-close"),
  workItemCancel: document.querySelector("#work-item-cancel"),
  workItemDialogError: document.querySelector("#work-item-dialog-error"),
  workItemDialogSuccess: document.querySelector("#work-item-dialog-success"),
  workItemReadOnly: document.querySelector("#work-item-read-only"),
  workItemStatusField: document.querySelector("#work-item-status-field"),
  workItemAssigneeField: document.querySelector("#work-item-assignee-field"),
  workItemDueField: document.querySelector("#work-item-due-field"),
  workItemTimezoneHelp: document.querySelector("#work-item-timezone-help"),
  workItemNoteField: document.querySelector("#work-item-note-field"),
  workItemEventsLoading: document.querySelector("#work-item-events-loading"),
  workItemEventsError: document.querySelector("#work-item-events-error"),
  workItemEventList: document.querySelector("#work-item-event-list"),
  workItemSave: document.querySelector("#work-item-save"),
};

const state = {
  apiPrefix: "/api/v1",
  maxUploadBytes: DEFAULT_MAX_FILE_BYTES,
  health: null,
  authStatus: null,
  authMode: "login",
  user: null,
  inputMode: "text",
  selectedFile: null,
  reviewBusy: false,
  reviewPage: 1,
  reviewPages: 1,
  reviewTotal: 0,
  reviewFilters: { q: "", status: "", includeDeleted: false },
  workPage: 1,
  workPages: 1,
  workTotal: 0,
  workFilters: { kind: "", status: "", assignee: "", overdue: false },
  workItems: [],
  currentReviewId: null,
  currentReview: null,
  currentReviewDeleted: false,
  activeRisk: "all",
  reportFindings: [],
  reportObligations: [],
  reviewWorkItems: [],
  reviewWorkItemsLoading: false,
  currentWorkItem: null,
  workItemReturnFocus: null,
  members: [],
  pendingConfirm: null,
  dashboardRequestVersion: 0,
  workRequestVersion: 0,
  reviewWorkRequestVersion: 0,
  workItemRequestVersion: 0,
};

function createElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function formatBytes(bytes) {
  const numeric = Number(bytes);
  if (!Number.isFinite(numeric)) return "未知大小";
  if (numeric < 1024) return `${numeric} B`;
  if (numeric < 1024 * 1024) return `${(numeric / 1024).toFixed(1)} KB`;
  return `${(numeric / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "时间未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatDueDate(value) {
  if (!value) return "未设置截止时间";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "截止时间未知";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function localDateTimeValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}

function explicitDueAt(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function formatNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toLocaleString("zh-CN") : "0";
}

function percent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "0%";
  return `${Math.round(Math.max(0, Math.min(1, numeric)) * 100)}%`;
}

function passwordPolicyError(value) {
  if (value.length < 12) return "密码至少需要 12 个字符。";
  if (value.length > 256) return "密码不能超过 256 个字符。";
  const categories = [
    /\p{Ll}/u.test(value),
    /\p{Lu}/u.test(value),
    /\p{N}/u.test(value),
    /[^\p{L}\p{N}]/u.test(value),
  ].filter(Boolean).length;
  if (categories < 3) {
    return "密码需在小写字母、大写字母、数字、符号四类中至少包含三类。";
  }
  return null;
}

function canManageMembers(user = state.user) {
  return user?.role === "owner" || user?.role === "admin";
}

function canCreateReviews(user = state.user) {
  return user?.role !== "viewer";
}

function canSubmitFeedback(user = state.user) {
  return user?.role !== "viewer";
}

function isPrivileged(user = state.user) {
  return user?.role === "owner" || user?.role === "admin";
}

function canMutateOperations(user = state.user) {
  return Boolean(user) && user.role !== "viewer";
}

function canEditWorkItem(item, user = state.user) {
  if (!canMutateOperations(user)) return false;
  if (isPrivileged(user)) return true;
  if (user.role !== "reviewer") return false;
  return !item?.assignee_user_id || item.assignee_user_id === user.user_id;
}

function reviewCreatorId(review) {
  return (
    review?.created_by_user_id ||
    review?.creator_user_id ||
    review?.created_by?.user_id ||
    review?.metadata?.created_by_user_id ||
    null
  );
}

function canManageReviewLifecycle(review, user = state.user) {
  if (!user) return false;
  if (user.role === "owner" || user.role === "admin") return true;
  if (user.role !== "reviewer") return false;
  const creatorId = reviewCreatorId(review);
  return Boolean(creatorId && creatorId === user.user_id);
}

function apiEndpoint(path) {
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith("/api/")) return path;
  const prefix = state.apiPrefix === "/" ? "" : state.apiPrefix.replace(/\/$/, "");
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${prefix}${suffix}` || "/";
}

function detailMessage(payload, fallback) {
  const detail = payload?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object" && typeof detail.message === "string") {
    return detail.message;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((item) => typeof item === "string" && item.trim());
    if (messages.length) return messages.join("；");
  }
  if (typeof payload?.message === "string" && payload.message.trim()) return payload.message;
  return fallback;
}

function normalizeApiError(status, payload) {
  if (status === 400) return detailMessage(payload, "请求内容无法处理，请检查后重试。");
  if (status === 401) return "登录已失效，请重新登录。";
  if (status === 403) return detailMessage(payload, "你没有执行此操作的权限。");
  if (status === 404) return detailMessage(payload, "没有找到这条记录，或你无权访问。");
  if (status === 409) return detailMessage(payload, "当前状态无法完成这个操作，请刷新后重试。");
  if (status === 413) return `合同文件太大，请控制在 ${formatBytes(state.maxUploadBytes)} 以内。`;
  if (status === 422) {
    return detailMessage(payload, "提交内容无法识别，请检查必填项或更换合同文件。");
  }
  if (status >= 500) return detailMessage(payload, "服务暂时没有完成请求，请稍后重试。");
  return detailMessage(payload, "请求没有成功，请稍后重试。");
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  const response = await fetch(path === "/health" ? "/health" : apiEndpoint(path), {
    ...options,
    headers,
    credentials: "include",
  });

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (response.status !== 204 && contentType.includes("application/json")) {
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && state.user && !path.startsWith("/auth/")) {
      window.setTimeout(expireSession, 0);
    }
    throw new ApiError(normalizeApiError(response.status, payload), response.status, payload);
  }
  return payload;
}

function showInlineError(element, message) {
  element.textContent = message;
  element.hidden = false;
}

function clearInlineError(element) {
  element.textContent = "";
  element.hidden = true;
}

function showInlineSuccess(element, message) {
  element.textContent = message;
  element.hidden = false;
}

function clearInlineSuccess(element) {
  element.textContent = "";
  element.hidden = true;
}

function showToast(message, { error = false } = {}) {
  const toast = createElement("div", `toast${error ? " is-error" : ""}`, message);
  elements.toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

function setButtonBusy(button, busy, busyText = "处理中……") {
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.textContent = busyText;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
    delete button.dataset.originalText;
  }
}

function userName(user) {
  return user?.display_name || user?.name || user?.email || "当前用户";
}

function setUser(user) {
  state.user = user;
  const name = userName(user);
  elements.sidebarUserName.textContent = name;
  elements.sidebarUserEmail.textContent = user?.email || "";
  elements.userAvatar.textContent = name.trim().slice(0, 1) || "用";
  elements.dashboardWelcome.textContent = `${name}，这里是当前组织的审阅进展和近期记录。`;
  const showAdmin = canManageMembers(user);
  elements.adminOnly.forEach((element) => {
    element.hidden = !showAdmin;
  });
  const showCreate = canCreateReviews(user);
  elements.reviewCreateOnly.forEach((element) => {
    element.hidden = !showCreate;
  });
  renderAccount();
}

function renderAccount() {
  const user = state.user || {};
  elements.accountName.textContent = userName(user);
  elements.accountEmail.textContent = user.email || "—";
  elements.accountOrganization.textContent = user.organization_name || "—";
  elements.accountRole.textContent = ROLE_LABELS[user.role] || user.role || "—";
  elements.accountRoleDescription.textContent = ROLE_DESCRIPTIONS[user.role] || "";
  elements.accountStatus.textContent = USER_STATUS_LABELS[user.status] || user.status || "—";
}

function setServiceState(health, error = null) {
  elements.authServiceState.classList.toggle("is-ready", Boolean(health) && !error);
  elements.authServiceState.classList.toggle("is-error", Boolean(error));
  if (error) {
    elements.authServiceText.textContent = "服务暂时不可用";
  } else if (health?.ai_enabled) {
    elements.authServiceText.textContent = "AI 增强审阅可用";
  } else if (health) {
    elements.authServiceText.textContent = "本地审阅服务正常";
  }
}

function setAuthMode(mode) {
  state.authMode = mode;
  clearInlineError(elements.authError);
  const isRegister = mode === "register";
  const isBootstrap = Boolean(state.authStatus?.bootstrap_required);
  elements.loginForm.hidden = isRegister;
  elements.registerForm.hidden = !isRegister;
  elements.authEyebrow.textContent = isRegister
    ? isBootstrap
      ? "首次设置"
      : "创建账号"
    : "欢迎回来";
  elements.authTitle.textContent = isRegister
    ? isBootstrap
      ? "创建第一个管理员账号"
      : "创建 ContractGuard 账号"
    : "登录 ContractGuard";
  elements.authDescription.textContent = isRegister
    ? isBootstrap
      ? "填写组织和管理员信息，完成当前服务的首次设置。"
      : "创建工作账号后开始管理合同审阅。"
    : "使用你的工作账号继续审阅。";

  const canSwitch = Boolean(state.authStatus?.registration_enabled) && !isBootstrap;
  elements.authSwitch.hidden = !canSwitch;
  elements.authSwitch.textContent = isRegister ? "已有账号？返回登录" : "还没有账号？创建账号";
  window.setTimeout(() => {
    const target = isRegister
      ? document.querySelector("#register-organization")
      : document.querySelector("#login-email");
    target?.focus();
  }, 0);
}

function showAuth(mode = "login") {
  elements.appView.hidden = true;
  elements.authView.hidden = false;
  elements.authLoading.hidden = true;
  elements.authContent.hidden = false;
  setAuthMode(mode);
}

function enterApp(user) {
  setUser(user || {});
  elements.authView.hidden = true;
  elements.appView.hidden = false;
  clearInlineError(elements.authError);
  if (!window.location.hash) {
    window.history.replaceState(null, "", "#dashboard");
  }
  handleRoute();
}

function expireSession() {
  if (!state.user) return;
  state.user = null;
  state.currentReview = null;
  showToast("登录已失效，请重新登录。", { error: true });
  showAuth("login");
}

async function initialize() {
  elements.authView.hidden = false;
  elements.authLoading.hidden = false;
  elements.authContent.hidden = true;
  let healthError = null;
  try {
    const health = await request("/health");
    state.health = health;
    if (health?.api_prefix) state.apiPrefix = health.api_prefix;
    if (Number.isFinite(health?.max_upload_bytes) && health.max_upload_bytes > 0) {
      state.maxUploadBytes = health.max_upload_bytes;
      elements.fileLimitLabel.textContent =
        `支持 PDF、Word、TXT、Markdown；服务允许的最大文件为 ${formatBytes(state.maxUploadBytes)}`;
    }
  } catch (error) {
    healthError = error;
  }
  setServiceState(state.health, healthError);

  try {
    state.authStatus = await request("/auth/status");
    if (state.authStatus?.bootstrap_required) {
      showAuth("register");
      return;
    }
    try {
      const session = await request("/auth/me");
      enterApp(session?.user);
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      showAuth("login");
    }
  } catch (error) {
    elements.authLoading.hidden = true;
    elements.authContent.hidden = false;
    showInlineError(
      elements.authError,
      error?.message || "无法确认登录状态，请检查服务后刷新页面。",
    );
    elements.loginForm.hidden = true;
    elements.registerForm.hidden = true;
  }
}

async function handleLogin(event) {
  event.preventDefault();
  if (!elements.loginForm.reportValidity()) return;
  clearInlineError(elements.authError);
  const submit = elements.loginForm.querySelector("button[type='submit']");
  const form = new FormData(elements.loginForm);
  setButtonBusy(submit, true, "正在登录……");
  try {
    const payload = await request("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: String(form.get("email") || "").trim(),
        password: String(form.get("password") || ""),
      }),
    });
    elements.loginForm.reset();
    enterApp(payload?.user);
  } catch (error) {
    showInlineError(elements.authError, error?.message || "登录失败，请检查账号信息。" );
  } finally {
    setButtonBusy(submit, false);
  }
}

async function handleRegistration(event) {
  event.preventDefault();
  if (!elements.registerForm.reportValidity()) return;
  clearInlineError(elements.authError);
  const submit = elements.registerForm.querySelector("button[type='submit']");
  const form = new FormData(elements.registerForm);
  const password = String(form.get("password") || "");
  const policyError = passwordPolicyError(password);
  if (policyError) {
    showInlineError(elements.authError, policyError);
    document.querySelector("#register-password")?.focus();
    return;
  }
  setButtonBusy(submit, true, "正在创建……");
  try {
    const payload = await request("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        organization_name: String(form.get("organization_name") || "").trim(),
        display_name: String(form.get("display_name") || "").trim(),
        email: String(form.get("email") || "").trim(),
        password,
      }),
    });
    state.authStatus = { ...state.authStatus, bootstrap_required: false };
    elements.registerForm.reset();
    enterApp(payload?.user);
  } catch (error) {
    showInlineError(elements.authError, error?.message || "账号创建失败，请检查填写内容。" );
  } finally {
    setButtonBusy(submit, false);
  }
}

function parseRoute() {
  const hash = window.location.hash.replace(/^#\/?/, "") || "dashboard";
  if (
    hash === "dashboard" ||
    hash === "work" ||
    hash === "reviews" ||
    hash === "new" ||
    hash === "account" ||
    hash === "admin"
  ) {
    return { name: hash, id: null };
  }
  if (hash.startsWith("review/")) {
    const encodedId = hash.slice("review/".length);
    try {
      return { name: "detail", id: decodeURIComponent(encodedId) };
    } catch {
      return { name: "reviews", id: null };
    }
  }
  return { name: "dashboard", id: null };
}

function updateNavigation(routeName) {
  const activeName = routeName === "detail" ? "reviews" : routeName;
  elements.routeLinks.forEach((link) => {
    if (link.dataset.routeLink === activeName) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

function showView(name) {
  elements.views.forEach((view) => {
    view.hidden = view.dataset.view !== name;
  });
  updateNavigation(name);
  window.scrollTo({ top: 0, behavior: "auto" });
  elements.workspace.focus({ preventScroll: true });
}

function handleRoute() {
  if (!state.user) return;
  const route = parseRoute();
  if (route.name === "new" && !canCreateReviews()) {
    showToast("当前账号为只读成员，不能新建合同审阅。", { error: true });
    window.history.replaceState(null, "", "#reviews");
    showView("reviews");
    document.title = "审阅记录 · ContractGuard";
    void loadReviewList();
    return;
  }
  if (route.name === "admin" && !canManageMembers()) {
    showToast("当前账号没有成员与日志管理权限。", { error: true });
    window.history.replaceState(null, "", "#account");
    showView("account");
    document.title = "账户 · ContractGuard";
    renderAccount();
    return;
  }
  showView(route.name);
  if (route.name === "dashboard") {
    document.title = "工作台 · ContractGuard";
    void loadDashboard();
  } else if (route.name === "work") {
    document.title = "处置中心 · ContractGuard";
    void (async () => {
      await ensureAssignableMembers();
      populateWorkStatusFilter();
      populateWorkAssigneeFilter();
      await loadWorkItems();
    })();
  } else if (route.name === "reviews") {
    document.title = "审阅记录 · ContractGuard";
    void loadReviewList();
  } else if (route.name === "new") {
    document.title = "新建审阅 · ContractGuard";
    clearInlineError(elements.reviewError);
  } else if (route.name === "account") {
    document.title = "账户与安全 · ContractGuard";
    renderAccount();
  } else if (route.name === "admin") {
    document.title = "成员与日志 · ContractGuard";
    clearInlineError(elements.adminAccessError);
    elements.adminContent.hidden = false;
    void (async () => {
      await loadMembers();
      if (!elements.adminContent.hidden) await loadAuditLogs();
    })();
  } else if (route.name === "detail" && route.id) {
    document.title = "审阅详情 · ContractGuard";
    void loadReviewDetail(route.id);
  }
}

function reviewId(item) {
  return item?.review_id || item?.id || "";
}

function reviewTitle(item) {
  return (
    item?.document?.filename ||
    item?.document_name ||
    item?.filename ||
    item?.contract_id ||
    "未命名合同"
  );
}

function isDeletedReview(item) {
  return Boolean(item?.deleted_at || item?.is_deleted || item?.deleted);
}

function highestRisk(item) {
  return (
    item?.highest_risk ||
    item?.highest_risk_level ||
    item?.summary?.highest_risk_level ||
    item?.report?.summary?.highest_risk_level ||
    null
  );
}

function statusBadge(status) {
  const normalized = status || "unknown";
  const badge = createElement(
    "span",
    `status-badge status-${normalized}`,
    STATUS_LABELS[normalized] || normalized,
  );
  return badge;
}

function renderRecordItem(item, { actions = true } = {}) {
  const id = reviewId(item);
  const deleted = isDeletedReview(item);
  const article = createElement("article", `record-item${deleted ? " is-deleted" : ""}`);
  const main = createElement("div", "record-main");
  const titleLine = createElement("div", "record-title-line");
  const title = createElement("a", "record-title", reviewTitle(item));
  title.href = id ? `#review/${encodeURIComponent(id)}` : "#reviews";
  titleLine.append(title, statusBadge(item?.status));
  if (deleted) titleLine.append(createElement("span", "deleted-badge", "已删除"));
  main.append(titleLine);

  const meta = createElement("div", "record-meta");
  meta.append(createElement("span", "", formatDate(item?.updated_at || item?.created_at)));
  if (item?.contract_id) meta.append(createElement("span", "", `合同编号：${item.contract_id}`));
  const risk = highestRisk(item);
  if (risk) meta.append(createElement("span", "", `最高风险：${RISK_LABELS[risk] || risk}`));
  main.append(meta);
  article.append(main);

  if (actions && id) {
    const actionBox = createElement("div", "record-actions");
    const view = createElement("a", "button button-secondary", "查看详情");
    view.href = `#review/${encodeURIComponent(id)}`;
    actionBox.append(view);
    if (canManageReviewLifecycle(item)) {
      const action = createElement(
        "button",
        deleted ? "button button-secondary" : "button button-quiet",
        deleted ? "恢复" : "删除",
      );
      action.type = "button";
      action.dataset.reviewAction = deleted ? "restore" : "delete";
      action.dataset.reviewId = id;
      action.dataset.reviewTitle = reviewTitle(item);
      actionBox.append(action);
    }
    article.append(actionBox);
  }
  return article;
}

function renderRecordList(container, items, options = {}) {
  container.replaceChildren();
  if (!Array.isArray(items) || items.length === 0) {
    const empty = createElement("div", "empty-state");
    empty.append(
      createElement("strong", "", options.emptyTitle || "还没有审阅记录"),
      createElement("span", "", options.emptyCopy || "提交第一份合同后，记录会显示在这里。"),
    );
    if (options.showCreate !== false && canCreateReviews()) {
      const link = createElement("a", "button button-primary", "新建审阅");
      link.href = "#new";
      empty.append(link);
    }
    container.append(empty);
    return;
  }
  items.forEach((item) => container.append(renderRecordItem(item, options)));
}

async function loadOperationsSummary() {
  elements.operationsSummaryLoading.hidden = false;
  elements.operationsSummaryContent.hidden = true;
  clearInlineError(elements.operationsSummaryError);
  try {
    const payload = await request("/operations/summary");
    elements.operationMyOpen.textContent = formatNumber(payload?.my_open);
    elements.operationOverdue.textContent = formatNumber(payload?.overdue);
    elements.operationHighRiskOpen.textContent = formatNumber(payload?.high_risk_open);
    elements.operationPendingApprovals.textContent = formatNumber(payload?.pending_approvals);
    elements.operationCompletedWeek.textContent = formatNumber(payload?.completed_this_week);
    elements.operationsSummaryContent.hidden = false;
  } catch (error) {
    showInlineError(
      elements.operationsSummaryError,
      error?.message || "处置摘要加载失败；审阅记录仍可继续使用。",
    );
  } finally {
    elements.operationsSummaryLoading.hidden = true;
  }
}

async function loadDashboard() {
  const requestVersion = ++state.dashboardRequestVersion;
  elements.dashboardLoading.hidden = false;
  elements.dashboardContent.hidden = false;
  elements.reviewSummaryContent.hidden = true;
  clearInlineError(elements.dashboardError);
  void loadOperationsSummary();
  try {
    const payload = await request("/dashboard/summary");
    if (requestVersion !== state.dashboardRequestVersion) return;
    elements.metricTotal.textContent = formatNumber(payload?.total_reviews);
    elements.metricCompleted.textContent = formatNumber(payload?.completed_reviews);
    elements.metricHighRisk.textContent = formatNumber(payload?.high_risk_reviews);
    elements.metricFailed.textContent = formatNumber(payload?.failed_reviews);
    renderRecordList(elements.recentReviewList, payload?.recent_reviews || [], {
      actions: false,
      emptyTitle: "还没有近期审阅",
      emptyCopy: "新建审阅后，最新记录会显示在这里。",
    });
    elements.reviewSummaryContent.hidden = false;
  } catch (error) {
    if (requestVersion !== state.dashboardRequestVersion) return;
    showInlineError(
      elements.dashboardError,
      error?.message || "工作台加载失败，请稍后重试。",
    );
  } finally {
    if (requestVersion === state.dashboardRequestVersion) {
      elements.dashboardLoading.hidden = true;
    }
  }
}

function workStatusValues(kind) {
  if (kind && WORK_STATUS_OPTIONS[kind]) return WORK_STATUS_OPTIONS[kind];
  return [...new Set([...WORK_STATUS_OPTIONS.finding, ...WORK_STATUS_OPTIONS.obligation])];
}

function populateWorkStatusFilter() {
  const selected = elements.workStatus.value || state.workFilters.status;
  const values = workStatusValues(elements.workKind.value);
  elements.workStatus.replaceChildren(createOption("", "全部状态", selected));
  values.forEach((value) => {
    elements.workStatus.append(createOption(value, WORK_STATUS_LABELS[value] || value, selected));
  });
  if (!values.includes(selected)) elements.workStatus.value = "";
}

async function ensureAssignableMembers() {
  if (!isPrivileged() || state.members.length > 0) return;
  try {
    const payload = await request("/users");
    state.members = Array.isArray(payload?.items) ? payload.items : [];
  } catch {
    // The work queue remains usable with the current-user and unassigned filters.
  }
}

function populateWorkAssigneeFilter() {
  const selected = elements.workAssignee.value || state.workFilters.assignee;
  const options = [
    createOption("", "全部负责人", selected),
    createOption("me", "由我负责", selected),
    createOption("unassigned", "尚未指派", selected),
  ];
  if (isPrivileged()) {
    state.members
      .filter((member) => member.status === "active" && member.role !== "viewer")
      .forEach((member) => {
        const id = member.user_id || member.id;
        if (!id) return;
        const label = member.display_name
          ? `${member.display_name} · ${member.email || "无邮箱"}`
          : member.email || `成员 ${id}`;
        options.push(createOption(id, label, selected));
      });
  }
  elements.workAssignee.replaceChildren(...options);
  if (!options.some((option) => option.value === selected)) elements.workAssignee.value = "";
}

function workItemAssigneeName(item) {
  if (!item?.assignee_user_id) return "尚未指派";
  if (item.assignee_display_name) return item.assignee_display_name;
  if (item.assignee_email) return item.assignee_email;
  if (item.assignee_user_id === state.user?.user_id) return `${userName(state.user)}（我）`;
  const member = state.members.find(
    (candidate) => (candidate.user_id || candidate.id) === item.assignee_user_id,
  );
  return member?.display_name || member?.email || "组织成员";
}

function isWorkItemOverdue(item) {
  if (!item?.due_at || TERMINAL_WORK_STATUSES.has(item.status)) return false;
  const due = new Date(item.due_at);
  return !Number.isNaN(due.getTime()) && due.getTime() < Date.now();
}

function renderWorkItemCard(item) {
  const article = createElement("article", "work-item-card");
  article.dataset.workItemId = item.work_item_id || "";

  const main = createElement("div", "work-item-card-main");
  const top = createElement("div", "work-item-card-top");
  const chips = createElement("div", "work-item-chips");
  chips.append(
    createElement("span", "kind-chip", WORK_KIND_LABELS[item.kind] || item.kind || "工作项"),
    createElement(
      "span",
      `work-status-chip status-${item.status || "unknown"}`,
      WORK_STATUS_LABELS[item.status] || item.status || "状态未知",
    ),
  );
  if (item.risk_level) {
    const risk = createElement("span", "risk-chip", RISK_LABELS[item.risk_level] || item.risk_level);
    risk.dataset.risk = item.risk_level;
    chips.append(risk);
  }
  if (isWorkItemOverdue(item)) chips.append(createElement("span", "overdue-chip", "已逾期"));
  top.append(chips);
  main.append(top);

  const title = createElement("h3");
  const reviewLink = createElement("a", "work-item-title", item.title || "未命名工作项");
  reviewLink.href = `#review/${encodeURIComponent(item.review_id || "")}`;
  title.append(reviewLink);
  main.append(title);
  main.append(createElement("p", "work-item-document", item.document_name || "审阅记录"));

  const meta = createElement("div", "work-item-meta");
  meta.append(
    createElement("span", "", `负责人：${workItemAssigneeName(item)}`),
    createElement("span", isWorkItemOverdue(item) ? "is-overdue" : "", `截止：${formatDueDate(item.due_at)}`),
    createElement("span", "", `更新：${formatDate(item.updated_at)}`),
  );
  main.append(meta);
  article.append(main);

  const actions = createElement("div", "work-item-card-actions");
  const openReview = createElement("a", "button button-secondary", "查看审阅");
  openReview.href = `#review/${encodeURIComponent(item.review_id || "")}`;
  const inspect = createElement(
    "button",
    canEditWorkItem(item) ? "button button-primary" : "button button-secondary",
    canEditWorkItem(item) ? "处置工作项" : "查看工作项",
  );
  inspect.type = "button";
  inspect.dataset.workItemAction = "open";
  inspect.dataset.workItemId = item.work_item_id || "";
  actions.append(openReview, inspect);
  article.append(actions);
  return article;
}

function renderWorkItemList(items) {
  elements.workItemList.replaceChildren();
  if (!Array.isArray(items) || items.length === 0) {
    const filtered = Boolean(
      state.workFilters.kind ||
      state.workFilters.status ||
      state.workFilters.assignee ||
      state.workFilters.overdue,
    );
    const empty = createElement("div", "empty-state");
    empty.append(
      createElement("strong", "", filtered ? "没有符合条件的工作项" : "当前没有需要处置的工作项"),
      createElement(
        "span",
        "",
        filtered
          ? "可以调整类型、状态、负责人或逾期条件后重试。"
          : "完成合同审阅后，风险和义务会在这里形成可跟进的工作项。",
      ),
    );
    elements.workItemList.append(empty);
    return;
  }
  items.forEach((item) => elements.workItemList.append(renderWorkItemCard(item)));
}

async function loadWorkItems() {
  const requestVersion = ++state.workRequestVersion;
  elements.workLoading.hidden = false;
  elements.workItemList.setAttribute("aria-busy", "true");
  clearInlineError(elements.workError);
  const query = new URLSearchParams({
    page: String(state.workPage),
    page_size: String(WORK_PAGE_SIZE),
    overdue: String(state.workFilters.overdue),
  });
  if (state.workFilters.kind) query.set("kind", state.workFilters.kind);
  if (state.workFilters.status) query.set("status", state.workFilters.status);
  if (state.workFilters.assignee) query.set("assignee", state.workFilters.assignee);
  try {
    const payload = await request(`/work-items?${query.toString()}`);
    if (requestVersion !== state.workRequestVersion) return;
    state.workItems = Array.isArray(payload?.items) ? payload.items : [];
    state.workTotal = Number(payload?.total) || 0;
    state.workPage = Number(payload?.page) || state.workPage;
    state.workPages = Math.max(1, Number(payload?.pages) || 1);
    renderWorkItemList(state.workItems);
    elements.workPagination.hidden = state.workTotal === 0;
    elements.workPreviousPage.disabled = state.workPage <= 1;
    elements.workNextPage.disabled = state.workPage >= state.workPages;
    elements.workPageStatus.textContent = `第 ${state.workPage} / ${state.workPages} 页，共 ${state.workTotal} 项`;
    elements.workResultSummary.textContent = `当前显示 ${state.workItems.length} 项，共 ${state.workTotal} 项处置工作。`;
  } catch (error) {
    if (requestVersion !== state.workRequestVersion) return;
    state.workItems = [];
    elements.workItemList.replaceChildren();
    elements.workPagination.hidden = true;
    elements.workResultSummary.textContent = "";
    showInlineError(elements.workError, error?.message || "处置工作项加载失败，请稍后重试。" );
  } finally {
    if (requestVersion === state.workRequestVersion) {
      elements.workLoading.hidden = true;
      elements.workItemList.removeAttribute("aria-busy");
    }
  }
}

function workItemById(workItemId) {
  return (
    state.reviewWorkItems.find((item) => item.work_item_id === workItemId) ||
    state.workItems.find((item) => item.work_item_id === workItemId) ||
    null
  );
}

function workItemForSource(kind, sourceOrdinal) {
  return (
    state.reviewWorkItems.find(
      (item) => item.kind === kind && Number(item.source_ordinal) === Number(sourceOrdinal),
    ) || null
  );
}

function workStatusRequiresNote(kind, targetStatus) {
  if (kind === "finding") return targetStatus === "resolved" || targetStatus === "accepted";
  return targetStatus === "waived";
}

function allowedWorkStatuses(item) {
  const current = item?.status || "";
  if (!canEditWorkItem(item)) return current ? [current] : [];
  const transitions = WORK_TRANSITIONS[item?.kind]?.[current] || [];
  if (!isPrivileged()) {
    return [
      current,
      ...transitions.filter((status) => !["accepted", "waived"].includes(status)),
    ];
  }
  return [current, ...transitions];
}

function renderInlineWorkItem(item, { loading = false } = {}) {
  const box = createElement("div", "inline-work-item");
  if (loading) {
    box.append(createElement("span", "inline-work-loading", "正在关联处置状态……"));
    return box;
  }
  if (!item) {
    box.append(createElement("span", "inline-work-loading", "这条内容暂未形成处置工作项。"));
    return box;
  }

  const summary = createElement("div", "inline-work-summary");
  const chips = createElement("div", "work-item-chips");
  chips.append(
    createElement(
      "span",
      `work-status-chip status-${item.status || "unknown"}`,
      WORK_STATUS_LABELS[item.status] || item.status || "状态未知",
    ),
  );
  if (isWorkItemOverdue(item)) chips.append(createElement("span", "overdue-chip", "已逾期"));
  summary.append(chips);
  const meta = createElement("div", "inline-work-meta");
  meta.append(
    createElement("span", "", `负责人：${workItemAssigneeName(item)}`),
    createElement(
      "span",
      isWorkItemOverdue(item) ? "is-overdue" : "",
      `截止：${formatDueDate(item.due_at)}`,
    ),
  );
  summary.append(meta);

  const action = createElement(
    "button",
    canEditWorkItem(item) ? "button button-primary button-small" : "button button-secondary button-small",
    canEditWorkItem(item) ? "处置" : "查看记录",
  );
  action.type = "button";
  action.dataset.workItemAction = "open";
  action.dataset.workItemId = item.work_item_id || "";
  box.append(summary, action);
  return box;
}

function updateReviewWorkSummaries() {
  if (state.reviewWorkItemsLoading) {
    elements.findingsWorkSummary.textContent = "正在加载处置状态……";
    elements.obligationsWorkSummary.textContent = "正在加载履行状态……";
    return;
  }
  const findingItems = state.reviewWorkItems.filter((item) => item.kind === "finding");
  const obligationItems = state.reviewWorkItems.filter((item) => item.kind === "obligation");
  const resolvedFindings = findingItems.filter((item) =>
    ["resolved", "accepted"].includes(item.status),
  ).length;
  const highRiskOpen = findingItems.filter(
    (item) =>
      ["critical", "high"].includes(item.risk_level) &&
      !["resolved", "accepted"].includes(item.status),
  ).length;
  const completedObligations = obligationItems.filter((item) =>
    ["completed", "waived"].includes(item.status),
  ).length;
  elements.findingsWorkSummary.textContent = findingItems.length
    ? `处置闭环 ${resolvedFindings}/${findingItems.length}${highRiskOpen ? ` · ${highRiskOpen} 条高风险待处理` : " · 高风险已清理"}`
    : "暂无处置工作项";
  elements.obligationsWorkSummary.textContent = obligationItems.length
    ? `履行闭环 ${completedObligations}/${obligationItems.length}`
    : "暂无义务工作项";
}

async function loadReviewWorkItems(reviewId) {
  const requestVersion = ++state.reviewWorkRequestVersion;
  state.reviewWorkItemsLoading = true;
  state.reviewWorkItems = [];
  clearInlineError(elements.detailWorkError);
  updateReviewWorkSummaries();
  renderFindings(state.reportFindings);
  renderObligations(state.reportObligations);
  try {
    const payload = await request(`/reviews/${encodeURIComponent(reviewId)}/work-items`);
    if (requestVersion !== state.reviewWorkRequestVersion || state.currentReviewId !== reviewId) {
      return;
    }
    state.reviewWorkItems = Array.isArray(payload?.items) ? payload.items : [];
  } catch (error) {
    if (requestVersion !== state.reviewWorkRequestVersion || state.currentReviewId !== reviewId) {
      return;
    }
    state.reviewWorkItems = [];
    showInlineError(
      elements.detailWorkError,
      error?.message || "处置工作项加载失败；合同审阅结果仍可继续查看。",
    );
  } finally {
    if (requestVersion === state.reviewWorkRequestVersion && state.currentReviewId === reviewId) {
      state.reviewWorkItemsLoading = false;
      updateReviewWorkSummaries();
      renderFindings(state.reportFindings);
      renderObligations(state.reportObligations);
    }
  }
}

function decisionTargets(review = state.currentReview) {
  if (
    !review ||
    review.status !== "completed" ||
    isDeletedReview(review) ||
    !canMutateOperations()
  ) {
    return [];
  }
  const current = review.decision_status || "draft";
  if (state.user?.role === "reviewer") {
    return ["draft", "rejected"].includes(current) ? ["in_review"] : [];
  }
  return isPrivileged() ? DECISION_TRANSITIONS[current] || [] : [];
}

function updateDecisionSubmitLabel() {
  const target = elements.decisionTarget.value;
  elements.decisionSubmit.textContent =
    target === "approved"
      ? "批准审阅"
      : target === "rejected"
        ? "驳回审阅"
        : state.currentReview?.decision_status === "draft"
          ? "提交复核"
          : "重新提交复核";
}

function renderDecision(review = state.currentReview) {
  const current = review?.decision_status || "draft";
  const label = DECISION_LABELS[current] || current;
  elements.detailDecisionStatus.className = `decision-badge decision-${current}`;
  elements.detailDecisionStatus.textContent = label;
  elements.approvalStatus.className = `decision-badge decision-${current}`;
  elements.approvalStatus.textContent = label;
  elements.approvalDescription.textContent =
    DECISION_DESCRIPTIONS[current] || "审阅决定状态未知，请刷新后重试。";
  clearInlineError(elements.decisionError);
  clearInlineSuccess(elements.decisionSuccess);

  const targets = decisionTargets(review);
  elements.decisionTarget.replaceChildren(
    ...targets.map((target) =>
      createOption(target, DECISION_LABELS[target] || target, targets.length === 1 ? target : ""),
    ),
  );
  elements.decisionForm.hidden = targets.length === 0;
  elements.decisionReadOnly.hidden = targets.length > 0;
  if (targets.length === 0) {
    if (isDeletedReview(review)) {
      elements.decisionReadOnly.textContent = "已删除的审阅只能查看审批状态；恢复记录后才能继续推进。";
    } else if (review?.status !== "completed") {
      elements.decisionReadOnly.textContent = "合同分析完成后，才能提交业务审批。";
    } else if (current === "in_review" && state.user?.role === "reviewer") {
      elements.decisionReadOnly.textContent = "已提交审批，正在等待管理员作出最终决定。";
    } else if (state.user?.role === "viewer") {
      elements.decisionReadOnly.textContent = "当前账号可以查看审批状态，但不能修改决定。";
    } else {
      elements.decisionReadOnly.textContent = "当前状态没有可执行的审批动作。";
    }
  }
  elements.decisionNote.value = "";
  if (targets.length) updateDecisionSubmitLabel();
}

async function submitDecision(event) {
  event.preventDefault();
  const review = state.currentReview;
  const reviewId = state.currentReviewId;
  if (!review || !reviewId) return;
  clearInlineError(elements.decisionError);
  clearInlineSuccess(elements.decisionSuccess);
  const target = elements.decisionTarget.value;
  const note = elements.decisionNote.value.trim();
  if (!target || !decisionTargets(review).includes(target)) {
    showInlineError(elements.decisionError, "当前审批动作已不可用，请刷新后重试。" );
    return;
  }
  if (target === "rejected" && !note) {
    showInlineError(elements.decisionError, "驳回审阅时必须填写审批说明。" );
    elements.decisionNote.focus();
    return;
  }

  setButtonBusy(elements.decisionSubmit, true, "正在更新……");
  try {
    const payload = await request(`/reviews/${encodeURIComponent(reviewId)}/decision`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        expected_version: review.state_version,
        status: target,
        note: note || null,
      }),
    });
    if (state.currentReviewId !== reviewId) return;
    state.currentReview = {
      ...state.currentReview,
      decision_status: payload.decision_status,
      state_version: payload.state_version,
      updated_at: payload.updated_at,
    };
    renderDecision(state.currentReview);
    showInlineSuccess(
      elements.decisionSuccess,
      `审批状态已更新为“${DECISION_LABELS[payload.decision_status] || payload.decision_status}”。`,
    );
    showToast("审阅决定已更新。" );
    void loadOperationsSummary();
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 409 &&
      String(error.message).includes("其他成员更新")
    ) {
      await loadReviewDetail(reviewId);
      showInlineError(elements.decisionError, "审批状态已被其他成员更新，页面已刷新，请重新确认。" );
    } else {
      showInlineError(elements.decisionError, error?.message || "审批状态更新失败，请稍后重试。" );
    }
  } finally {
    setButtonBusy(elements.decisionSubmit, false);
    if (!elements.decisionForm.hidden) updateDecisionSubmitLabel();
  }
}

function populateWorkItemStatusField(item) {
  const statuses = allowedWorkStatuses(item);
  elements.workItemStatusField.replaceChildren(
    ...statuses.map((status) =>
      createOption(status, WORK_STATUS_LABELS[status] || status, item.status),
    ),
  );
}

function populateWorkItemAssigneeField(item) {
  const selected =
    state.user?.role === "reviewer" && !item.assignee_user_id
      ? state.user.user_id
      : item.assignee_user_id || "";
  const options = [];
  if (isPrivileged()) {
    options.push(createOption("", "尚未指派", selected));
    const assignableMembers = state.members.filter(
      (member) => member.status === "active" && member.role !== "viewer",
    );
    if (
      item.assignee_user_id &&
      !assignableMembers.some(
        (member) => (member.user_id || member.id) === item.assignee_user_id,
      )
    ) {
      options.push(
        createOption(
          item.assignee_user_id,
          `${workItemAssigneeName(item)}（当前负责人）`,
          selected,
        ),
      );
    }
    assignableMembers.forEach((member) => {
        const id = member.user_id || member.id;
        if (!id) return;
        const label = member.display_name
          ? `${member.display_name} · ${member.email || "无邮箱"}`
          : member.email || `成员 ${id}`;
        options.push(createOption(id, label, selected));
      });
  } else if (state.user?.role === "reviewer") {
    if (item.assignee_user_id && item.assignee_user_id !== state.user.user_id) {
      options.push(createOption(item.assignee_user_id, workItemAssigneeName(item), selected));
    } else {
      options.push(createOption(state.user.user_id, `${userName(state.user)}（我）`, selected));
    }
  } else {
    options.push(createOption(item.assignee_user_id || "", workItemAssigneeName(item), selected));
  }
  elements.workItemAssigneeField.replaceChildren(...options);
}

function renderWorkItemDialog(item) {
  state.currentWorkItem = item;
  const currentRoute = parseRoute();
  const reviewIsDeleted =
    currentRoute.name === "detail" &&
    state.currentReviewId === item.review_id &&
    state.currentReviewDeleted;
  const editable = canEditWorkItem(item) && !reviewIsDeleted;
  elements.workItemDialogKind.textContent = WORK_KIND_LABELS[item.kind] || "工作项";
  elements.workItemDialogTitle.textContent = item.title || "未命名工作项";
  elements.workItemDialogContext.textContent = `${item.document_name || "审阅记录"} · 更新于 ${formatDate(item.updated_at)}`;
  clearInlineError(elements.workItemDialogError);
  clearInlineSuccess(elements.workItemDialogSuccess);
  populateWorkItemStatusField(item);
  populateWorkItemAssigneeField(item);
  elements.workItemDueField.value = localDateTimeValue(item.due_at);
  elements.workItemNoteField.value = item.note || "";
  elements.workItemReadOnly.hidden = editable;
  elements.workItemStatusField.disabled = !editable;
  elements.workItemAssigneeField.disabled = !editable;
  elements.workItemDueField.disabled = !editable;
  elements.workItemNoteField.disabled = !editable;
  elements.workItemSave.hidden = !editable;
  elements.workItemTimezoneHelp.textContent = item.due_at
    ? `当前截止时间：${formatDate(item.due_at)}；按当前设备时区编辑。`
    : "按当前设备时区保存为明确时间点。";
}

function workEventTitle(event) {
  if (event.action === "materialized") return "已从审阅结果创建工作项";
  if (event.action === "status_changed") {
    return `状态由“${WORK_STATUS_LABELS[event.from_status] || event.from_status}”变为“${WORK_STATUS_LABELS[event.to_status] || event.to_status}”`;
  }
  if (event.action === "assigned") return "已指派负责人";
  if (event.action === "unassigned") return "已取消负责人";
  if (event.action === "due_date_changed") return "已更新截止时间";
  return "已更新工作项";
}

function renderWorkItemEvents(events) {
  elements.workItemEventList.replaceChildren();
  const items = Array.isArray(events) ? [...events].reverse() : [];
  if (!items.length) {
    elements.workItemEventList.append(
      createElement("div", "empty-state compact-empty", "当前还没有可显示的变更记录。"),
    );
    return;
  }
  items.forEach((event) => {
    const article = createElement("article", "work-event-item");
    const marker = createElement("span", "work-event-marker");
    const body = createElement("div", "work-event-body");
    body.append(createElement("strong", "", workEventTitle(event)));
    const actor = event.actor_display_name || (event.actor_user_id ? "组织成员" : "系统");
    body.append(createElement("small", "", `${actor} · ${formatDate(event.created_at)}`));
    if (event.note) body.append(createElement("p", "", event.note));
    article.append(marker, body);
    elements.workItemEventList.append(article);
  });
}

async function loadWorkItemEvents(workItemId) {
  elements.workItemEventsLoading.hidden = false;
  clearInlineError(elements.workItemEventsError);
  elements.workItemEventList.replaceChildren();
  try {
    const payload = await request(`/work-items/${encodeURIComponent(workItemId)}/events`);
    if (state.currentWorkItem?.work_item_id !== workItemId) return;
    renderWorkItemEvents(payload?.items || []);
  } catch (error) {
    if (state.currentWorkItem?.work_item_id !== workItemId) return;
    showInlineError(
      elements.workItemEventsError,
      error?.message || "事件记录加载失败，请稍后重试。",
    );
  } finally {
    if (state.currentWorkItem?.work_item_id === workItemId) {
      elements.workItemEventsLoading.hidden = true;
    }
  }
}

async function openWorkItem(workItemId, trigger = null) {
  if (!workItemId) return;
  const requestVersion = ++state.workItemRequestVersion;
  state.workItemReturnFocus = trigger instanceof HTMLElement ? trigger : document.activeElement;
  let item = workItemById(workItemId);
  if (item) {
    await ensureAssignableMembers();
    renderWorkItemDialog(item);
    if (typeof elements.workItemDialog.showModal === "function") {
      if (!elements.workItemDialog.open) elements.workItemDialog.showModal();
    } else {
      elements.workItemDialog.setAttribute("open", "");
    }
    window.setTimeout(() => {
      (canEditWorkItem(item) ? elements.workItemStatusField : elements.workItemClose).focus();
    }, 0);
  }
  try {
    item = await request(`/work-items/${encodeURIComponent(workItemId)}`);
    if (requestVersion !== state.workItemRequestVersion) return;
    await ensureAssignableMembers();
    if (requestVersion !== state.workItemRequestVersion) return;
    if (!elements.workItemDialog.open) {
      renderWorkItemDialog(item);
      if (typeof elements.workItemDialog.showModal === "function") {
        elements.workItemDialog.showModal();
      } else {
        elements.workItemDialog.setAttribute("open", "");
      }
    } else {
      renderWorkItemDialog(item);
    }
    void loadWorkItemEvents(workItemId);
  } catch (error) {
    if (elements.workItemDialog.open) {
      showInlineError(elements.workItemDialogError, error?.message || "工作项加载失败，请稍后重试。" );
    } else {
      showToast(error?.message || "工作项加载失败，请稍后重试。", { error: true });
    }
  }
}

function closeWorkItemDialog() {
  state.workItemRequestVersion += 1;
  if (typeof elements.workItemDialog.close === "function" && elements.workItemDialog.open) {
    elements.workItemDialog.close();
  } else {
    elements.workItemDialog.removeAttribute("open");
    const target = state.workItemReturnFocus;
    state.currentWorkItem = null;
    state.workItemReturnFocus = null;
    if (target instanceof HTMLElement && target.isConnected) target.focus();
  }
}

function replaceCachedWorkItem(updated) {
  state.workItems = state.workItems.map((item) =>
    item.work_item_id === updated.work_item_id ? updated : item,
  );
  state.reviewWorkItems = state.reviewWorkItems.map((item) =>
    item.work_item_id === updated.work_item_id ? updated : item,
  );
  state.currentWorkItem = updated;
}

function sameDueAt(left, right) {
  if (!left && !right) return true;
  if (!left || !right) return false;
  const leftDate = new Date(left);
  const rightDate = new Date(right);
  if (Number.isNaN(leftDate.getTime()) || Number.isNaN(rightDate.getTime())) return left === right;
  return leftDate.getTime() === rightDate.getTime();
}

async function saveWorkItem(event) {
  event.preventDefault();
  const item = state.currentWorkItem;
  if (!item || !canEditWorkItem(item)) return;
  clearInlineError(elements.workItemDialogError);
  clearInlineSuccess(elements.workItemDialogSuccess);

  const status = elements.workItemStatusField.value;
  const assignee = elements.workItemAssigneeField.value || null;
  const dueAt = explicitDueAt(elements.workItemDueField.value);
  const noteText = elements.workItemNoteField.value.trim();
  const note = noteText || null;
  if (status !== item.status && workStatusRequiresNote(item.kind, status) && !noteText) {
    showInlineError(elements.workItemDialogError, "完成该处置状态前，请填写判断依据或处理说明。" );
    elements.workItemNoteField.focus();
    return;
  }

  const patch = { expected_version: item.state_version };
  if (status !== item.status) patch.status = status;
  if (assignee !== (item.assignee_user_id || null)) patch.assignee_user_id = assignee;
  if (!sameDueAt(dueAt, item.due_at)) patch.due_at = dueAt;
  if (note !== (item.note || null)) patch.note = note;
  if (Object.keys(patch).length === 1) {
    showInlineError(elements.workItemDialogError, "没有需要保存的变更。" );
    return;
  }

  setButtonBusy(elements.workItemSave, true, "正在保存……");
  try {
    const updated = await request(`/work-items/${encodeURIComponent(item.work_item_id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    replaceCachedWorkItem(updated);
    renderWorkItemDialog(updated);
    showInlineSuccess(elements.workItemDialogSuccess, "工作项已保存，事件时间线已更新。" );
    showToast("处置工作项已更新。" );
    updateReviewWorkSummaries();
    renderFindings(state.reportFindings);
    renderObligations(state.reportObligations);
    if (state.currentReviewId === updated.review_id) {
      clearInlineError(elements.decisionError);
      const remainingHighRisk = state.reviewWorkItems.filter(
        (candidate) =>
          candidate.kind === "finding" &&
          ["critical", "high"].includes(candidate.risk_level) &&
          !["resolved", "accepted"].includes(candidate.status),
      ).length;
      if (state.currentReview?.decision_status === "in_review" && remainingHighRisk === 0) {
        showInlineSuccess(
          elements.decisionSuccess,
          "高风险审批门禁已清除，可以继续批准这份审阅。",
        );
      }
    }
    if (parseRoute().name === "work") void loadWorkItems();
    void loadOperationsSummary();
    void loadWorkItemEvents(updated.work_item_id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      try {
        const latest = await request(`/work-items/${encodeURIComponent(item.work_item_id)}`);
        replaceCachedWorkItem(latest);
        renderWorkItemDialog(latest);
      } catch {
        // Keep the original conflict message when the latest value cannot be reloaded.
      }
      showInlineError(
        elements.workItemDialogError,
        String(error.message).includes("其他成员更新")
          ? "工作项已被其他成员更新，表单已刷新，请重新确认后保存。"
          : error.message,
      );
      void loadWorkItemEvents(item.work_item_id);
    } else {
      showInlineError(
        elements.workItemDialogError,
        error?.message || "工作项保存失败，请稍后重试。",
      );
    }
  } finally {
    setButtonBusy(elements.workItemSave, false);
  }
}

async function loadReviewList() {
  elements.reviewsLoading.hidden = false;
  elements.reviewList.setAttribute("aria-busy", "true");
  clearInlineError(elements.reviewsError);
  const query = new URLSearchParams({
    page: String(state.reviewPage),
    page_size: String(PAGE_SIZE),
    q: state.reviewFilters.q,
    status: state.reviewFilters.status,
    include_deleted: String(state.reviewFilters.includeDeleted),
  });
  try {
    const payload = await request(`/reviews?${query.toString()}`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    state.reviewTotal = Number(payload?.total) || 0;
    state.reviewPage = Number(payload?.page) || state.reviewPage;
    state.reviewPages = Math.max(1, Number(payload?.pages) || 1);
    renderRecordList(elements.reviewList, items, {
      actions: true,
      showCreate: state.reviewTotal === 0 && !state.reviewFilters.q && !state.reviewFilters.status,
      emptyTitle: state.reviewFilters.q || state.reviewFilters.status
        ? "没有符合条件的记录"
        : "还没有审阅记录",
      emptyCopy: state.reviewFilters.q || state.reviewFilters.status
        ? "请调整关键词或状态筛选后重试。"
        : "提交第一份合同后，记录会显示在这里。",
    });
    elements.reviewPagination.hidden = state.reviewTotal === 0;
    elements.previousPage.disabled = state.reviewPage <= 1;
    elements.nextPage.disabled = state.reviewPage >= state.reviewPages;
    elements.pageStatus.textContent = `第 ${state.reviewPage} / ${state.reviewPages} 页，共 ${state.reviewTotal} 条`;
  } catch (error) {
    elements.reviewList.replaceChildren();
    elements.reviewPagination.hidden = true;
    showInlineError(elements.reviewsError, error?.message || "审阅记录加载失败，请稍后重试。" );
  } finally {
    elements.reviewsLoading.hidden = true;
    elements.reviewList.removeAttribute("aria-busy");
  }
}

async function confirmOperation({ title, message, confirmText, danger = true }) {
  if (typeof elements.confirmDialog.showModal !== "function") {
    return window.confirm(message);
  }
  if (elements.confirmDialog.open) elements.confirmDialog.close("cancel");
  elements.confirmTitle.textContent = title;
  elements.confirmMessage.textContent = message;
  elements.confirmAction.textContent = confirmText;
  elements.confirmAction.className = danger
    ? "button button-danger"
    : "button button-primary";
  elements.confirmDialog.returnValue = "cancel";
  elements.confirmDialog.showModal();
  return new Promise((resolve) => {
    state.pendingConfirm = resolve;
  });
}

async function deleteReview(id, title, { fromDetail = false } = {}) {
  const confirmed = await confirmOperation({
    title: "删除这条审阅记录？",
    message: `“${title}”将进入已删除状态。你之后可以在“包含已删除记录”中找到并恢复它。`,
    confirmText: "确认删除",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await request(`/reviews/${encodeURIComponent(id)}`, { method: "DELETE" });
    showToast("审阅记录已删除。" );
    if (fromDetail) {
      await loadReviewDetail(id);
    } else {
      await loadReviewList();
    }
  } catch (error) {
    showToast(error?.message || "删除失败，请稍后重试。", { error: true });
  }
}

async function restoreReview(id, title, { fromDetail = false } = {}) {
  const confirmed = await confirmOperation({
    title: "恢复这条审阅记录？",
    message: `恢复“${title}”后，它会重新出现在正常的审阅记录中。`,
    confirmText: "确认恢复",
    danger: false,
  });
  if (!confirmed) return;
  try {
    await request(`/reviews/${encodeURIComponent(id)}/restore`, { method: "POST" });
    showToast("审阅记录已恢复。" );
    if (fromDetail) {
      await loadReviewDetail(id);
    } else {
      await loadReviewList();
    }
  } catch (error) {
    showToast(error?.message || "恢复失败，请稍后重试。", { error: true });
  }
}

async function loadReviewDetail(id) {
  state.currentReviewId = id;
  state.currentReview = null;
  elements.detailLoading.hidden = false;
  elements.detailContent.hidden = true;
  clearInlineError(elements.detailError);
  try {
    const payload = await request(`/reviews/${encodeURIComponent(id)}`);
    if (state.currentReviewId !== id) return;
    state.currentReview = payload;
    renderReviewDetail(payload);
    elements.detailContent.hidden = false;
  } catch (error) {
    showInlineError(elements.detailError, error?.message || "审阅详情加载失败，请稍后重试。" );
  } finally {
    if (state.currentReviewId === id) elements.detailLoading.hidden = true;
  }
}

function renderReviewDetail(payload) {
  const report = payload?.report || {};
  const findings = Array.isArray(report.findings)
    ? report.findings.map((finding, index) => ({
        ...finding,
        _sourceOrdinal: index,
        _displayIndex: index + 1,
      }))
    : [];
  findings.sort(
    (left, right) =>
      (RISK_ORDER[right.risk_level] || 0) - (RISK_ORDER[left.risk_level] || 0),
  );
  const obligations = Array.isArray(report.obligations)
    ? report.obligations.map((obligation, index) => ({
        ...obligation,
        _sourceOrdinal: index,
      }))
    : [];
  const contexts = Array.isArray(report.contexts) ? report.contexts : [];
  const quality = report.quality || {};
  const deleted = isDeletedReview(payload);
  state.currentReviewDeleted = deleted;
  state.reportFindings = findings;
  state.reportObligations = obligations;
  state.reviewWorkItems = [];
  state.reviewWorkItemsLoading = false;
  state.activeRisk = "all";

  elements.detailStatus.className = `status-badge status-${payload?.status || "unknown"}`;
  elements.detailStatus.textContent = STATUS_LABELS[payload?.status] || payload?.status || "状态未知";
  elements.detailDeletedBadge.hidden = !deleted;
  elements.detailTitle.textContent = reviewTitle(payload);
  const meta = [
    payload?.contract_id ? `合同编号：${payload.contract_id}` : null,
    `创建时间：${formatDate(payload?.created_at)}`,
    payload?.updated_at ? `最近更新：${formatDate(payload.updated_at)}` : null,
  ].filter(Boolean);
  elements.detailMeta.textContent = meta.join(" · ");
  elements.exportButton.href = apiEndpoint(
    `/reviews/${encodeURIComponent(state.currentReviewId)}/export?format=html`,
  );
  const canManageLifecycle = canManageReviewLifecycle(payload);
  elements.deleteReviewButton.hidden = deleted || !canManageLifecycle;
  elements.restoreReviewButton.hidden = !deleted || !canManageLifecycle;
  renderDecision(payload);

  const highRiskCount = findings.filter((item) =>
    ["critical", "high"].includes(item.risk_level),
  ).length;
  const highest = report.summary?.highest_risk_level;
  elements.summaryFindings.textContent = String(findings.length);
  elements.summaryHighest.textContent = highest
    ? `最高：${RISK_LABELS[highest] || highest}`
    : "未生成风险等级";
  elements.summaryHighRisk.textContent = String(highRiskCount);
  elements.summaryObligations.textContent = String(obligations.length);
  elements.summaryCoverage.textContent = percent(quality.evidence_coverage);

  renderModeNotice(payload?.status, Boolean(quality.llm_review_performed), findings.length, payload?.error);
  updateRiskFilterControls("all");
  renderFindings(findings);
  renderObligations(obligations);
  renderContexts(contexts, quality, report.analysis_notes);
  elements.contextDrawer.open = false;
  elements.legalNotice.textContent =
    typeof report.disclaimer === "string" && report.disclaimer.trim()
      ? report.disclaimer
      : "本结果仅用于辅助定位合同问题，不构成法律意见，也不能代替了解交易背景的专业人员审阅。";
  clearInlineError(elements.detailWorkError);
  if (payload?.status === "completed" && !deleted) {
    void loadReviewWorkItems(payload.review_id);
  } else {
    updateReviewWorkSummaries();
  }
}

function renderModeNotice(status, aiPerformed, findingCount, error) {
  elements.modeNotice.replaceChildren();
  if (status === "failed") {
    const strong = createElement("strong", "", "这次审阅没有完成。" );
    const copy = createElement("span", "", error ? ` ${error}` : " 请重新提交或联系管理员检查服务。" );
    elements.modeNotice.append(strong, copy);
    return;
  }
  if (status === "processing") {
    elements.modeNotice.append(
      createElement("strong", "", "这份合同仍在处理中。"),
      createElement("span", "", " 稍后刷新审阅详情可查看最新状态。"),
    );
    return;
  }
  const strong = createElement(
    "strong",
    "",
    aiPerformed ? "本次使用了 AI 增强审阅。" : "本次使用本地规则审阅。",
  );
  const copy = createElement(
    "span",
    "",
    findingCount === 0
      ? " 暂未发现具备原文证据的风险，但仍需人工复核。"
      : " 所有展示的风险均附有合同原文证据。",
  );
  elements.modeNotice.append(strong, copy);
}

function updateRiskFilterControls(risk) {
  elements.riskFilters.querySelectorAll("button[data-risk]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.risk === risk));
  });
}

function renderFindings(findings) {
  elements.findingList.replaceChildren();
  const visible =
    state.activeRisk === "all"
      ? findings
      : findings.filter((finding) => finding.risk_level === state.activeRisk);
  elements.riskResultStatus.textContent =
    state.activeRisk === "all"
      ? `当前显示全部 ${visible.length} 条风险提示。`
      : `当前显示 ${RISK_LABELS[state.activeRisk] || state.activeRisk} ${visible.length} 条。`;
  if (visible.length === 0) {
    const empty = createElement("div", "empty-state");
    empty.append(
      createElement(
        "strong",
        "",
        findings.length === 0 ? "暂未发现有原文证据支持的风险提示" : "这个等级暂无风险提示",
      ),
      createElement(
        "span",
        "",
        findings.length === 0
          ? "这不代表合同没有风险，请继续由了解交易背景的专业人员复核。"
          : "可以切换到“全部”查看其他等级。",
      ),
    );
    elements.findingList.append(empty);
    return;
  }

  visible.forEach((finding) => {
    const risk = finding.risk_level || "info";
    const card = createElement("article", "finding-card");
    card.dataset.risk = risk;
    if (finding.finding_id) card.dataset.findingId = finding.finding_id;

    const main = createElement("div", "finding-main");
    const topline = createElement("div", "finding-topline");
    const titleGroup = createElement("div");
    titleGroup.append(
      createElement("p", "finding-index", `风险 ${finding._displayIndex || ""}`),
      createElement("h3", "", finding.title || "需要进一步核对的条款"),
    );
    const chip = createElement("span", "risk-chip", RISK_LABELS[risk] || "风险提示");
    chip.dataset.risk = risk;
    topline.append(titleGroup, chip);
    main.append(topline);

    if (finding.description) {
      main.append(createElement("p", "finding-description", finding.description));
    }

    const evidence = Array.isArray(finding.evidence) ? finding.evidence : [];
    evidence.forEach((item) => {
      if (!item?.quote) return;
      const box = createElement("div", "evidence-box");
      box.append(
        createElement("span", "evidence-label", "合同原文"),
        createElement("blockquote", "", `“${item.quote}”`),
      );
      main.append(box);
    });
    card.append(main);

    if (finding.recommendation || (finding.finding_id && !state.currentReviewDeleted)) {
      const recommendation = createElement("div", "recommendation-box");
      if (finding.recommendation) {
        recommendation.append(
          createElement("span", "recommendation-label", "修改建议"),
          createElement("p", "", finding.recommendation),
        );
      }
      const actions = createElement("div", "finding-actions");
      if (finding.recommendation) {
        const copy = createElement("button", "button button-secondary", "复制建议");
        copy.type = "button";
        copy.dataset.findingAction = "copy";
        actions.append(copy);
      }
      if (finding.finding_id && !state.currentReviewDeleted && canSubmitFeedback()) {
        actions.prepend(createElement("span", "feedback-label", "这条提示是否有帮助？"));
        const accept = createElement("button", "button button-secondary", "有帮助");
        accept.type = "button";
        accept.dataset.findingAction = "feedback";
        accept.dataset.accepted = "true";
        const reject = createElement("button", "button button-secondary", "需要复核");
        reject.type = "button";
        reject.dataset.findingAction = "feedback";
        reject.dataset.accepted = "false";
        actions.append(accept, reject);
      }
      recommendation.append(actions);
      card.append(recommendation);
    }
    card.append(
      renderInlineWorkItem(
        workItemForSource("finding", finding._sourceOrdinal),
        { loading: state.reviewWorkItemsLoading },
      ),
    );
    elements.findingList.append(card);
  });
}

function renderObligations(obligations) {
  elements.obligationList.replaceChildren();
  if (obligations.length === 0) {
    elements.obligationList.append(
      createElement(
        "div",
        "empty-state",
        "本次没有提取到明确的履行义务，请结合合同全文人工核对。",
      ),
    );
    return;
  }
  obligations.forEach((obligation) => {
    const card = createElement("article", "obligation-card");
    card.append(createElement("div", "obligation-party", obligation.obligor || "主体未明确"));
    const copy = createElement("div", "obligation-copy");
    copy.append(createElement("p", "", obligation.action || "义务内容需要核对"));
    const details = [obligation.due_expression, obligation.condition].filter(Boolean).join("；");
    if (details) copy.append(createElement("small", "", `时间或条件：${details}`));
    if (obligation.evidence?.quote) {
      copy.append(createElement("small", "", `原文：${obligation.evidence.quote}`));
    }
    card.append(copy);
    card.append(
      renderInlineWorkItem(
        workItemForSource("obligation", obligation._sourceOrdinal),
        { loading: state.reviewWorkItemsLoading },
      ),
    );
    elements.obligationList.append(card);
  });
}

function renderContexts(contexts, quality, analysisNotes) {
  elements.contextList.replaceChildren();
  elements.contextCount.textContent = `${contexts.length} 条`;
  if (contexts.length === 0) {
    elements.contextList.append(
      createElement("div", "empty-state", "本次没有使用额外的知识库或历史偏好。"),
    );
  } else {
    contexts.forEach((context) => {
      const card = createElement("article", "context-card");
      const header = createElement("header");
      header.append(
        createElement("strong", "", context.citation || "审阅依据"),
        createElement(
          "span",
          "context-type",
          context.source === "memory" ? "历史偏好" : "知识库",
        ),
      );
      card.append(header, createElement("p", "", context.content || "无内容"));
      elements.contextList.append(card);
    });
  }

  elements.qualityPanel.replaceChildren();
  const qualityItems = [
    [quality.llm_review_performed ? "已调用" : "未调用", "AI 复核"],
    [String(quality.verified_finding_count ?? 0), "有原文证据的风险"],
    [percent(quality.completeness), "审阅流程完整度"],
  ];
  qualityItems.forEach(([value, label]) => {
    const item = createElement("div", "quality-item");
    item.append(createElement("strong", "", value), createElement("small", "", label));
    elements.qualityPanel.append(item);
  });

  const notes = [];
  if (Array.isArray(quality.warnings)) {
    quality.warnings.forEach((warning) => {
      const rejectedMatch = /^Rejected (\d+) finding/.exec(warning);
      if (rejectedMatch) {
        notes.push(`有 ${rejectedMatch[1]} 条缺少原文支持的候选风险已被自动剔除。`);
      } else {
        notes.push(WARNING_TRANSLATIONS[warning] || warning);
      }
    });
  }
  if (Array.isArray(analysisNotes)) {
    analysisNotes.forEach((note) => {
      if (typeof note === "string" && note.trim()) notes.push(WARNING_TRANSLATIONS[note] || note);
    });
  }
  if (notes.length > 0) {
    const box = createElement("div", "analysis-notes");
    box.append(createElement("strong", "", "审阅说明"));
    const list = createElement("ul");
    notes.forEach((note) => list.append(createElement("li", "", note)));
    box.append(list);
    elements.qualityPanel.append(box);
  }
}

async function copyFindingRecommendation(card, button) {
  const recommendation = card.querySelector(".recommendation-box p")?.textContent || "";
  const title = card.querySelector("h3")?.textContent || "合同风险";
  try {
    await navigator.clipboard.writeText(`${title}\n${recommendation}`.trim());
    const original = button.textContent;
    button.textContent = "已复制";
    showToast("修改建议已复制。" );
    window.setTimeout(() => {
      button.textContent = original;
    }, 1600);
  } catch {
    showToast("浏览器未允许复制，请手动选择修改建议。", { error: true });
  }
}

async function submitFindingFeedback(card, button, accepted) {
  const findingId = card.dataset.findingId;
  if (!findingId || !state.currentReviewId) return;
  const buttons = [...card.querySelectorAll("[data-finding-action='feedback']")];
  buttons.forEach((item) => {
    item.disabled = true;
  });
  try {
    await request(`/reviews/${encodeURIComponent(state.currentReviewId)}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ finding_id: findingId, accepted }),
    });
    const actionBox = button.parentElement;
    buttons.forEach((item) => item.remove());
    const status = createElement(
      "span",
      "feedback-status",
      accepted ? "已记录：有帮助" : "已记录：需要复核",
    );
    actionBox?.append(status);
    showToast("反馈已保存。" );
  } catch (error) {
    buttons.forEach((item) => {
      item.disabled = false;
    });
    showToast(error?.message || "反馈保存失败，请稍后重试。", { error: true });
  }
}

function switchInputMode(mode, { focus = false } = {}) {
  state.inputMode = mode;
  elements.tabs.forEach((tab) => {
    const active = tab.dataset.mode === mode;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    if (focus && active) tab.focus();
  });
  elements.textPanel.hidden = mode !== "text";
  elements.filePanel.hidden = mode !== "file";
  clearInlineError(elements.reviewError);
}

function updateCharacterCount() {
  elements.characterCount.textContent =
    `${elements.contractText.value.length.toLocaleString("zh-CN")} 字`;
}

function clearSelectedFile({ focus = true } = {}) {
  state.selectedFile = null;
  elements.contractFile.value = "";
  elements.dropZone.hidden = false;
  elements.selectedFile.hidden = true;
  if (focus) elements.chooseFileButton.focus();
}

function selectFile(file) {
  if (!file) return;
  if (file.size > state.maxUploadBytes) {
    clearSelectedFile({ focus: false });
    showInlineError(
      elements.reviewError,
      `文件超过 ${formatBytes(state.maxUploadBytes)}。请压缩文件，或粘贴合同文字。`,
    );
    elements.chooseFileButton.focus();
    return;
  }
  state.selectedFile = file;
  elements.selectedFileName.textContent = file.name || "未命名合同";
  elements.selectedFileSize.textContent = formatBytes(file.size);
  elements.dropZone.hidden = true;
  elements.selectedFile.hidden = false;
  clearInlineError(elements.reviewError);
  elements.removeFileButton.focus();
}

function resetNewReviewForm() {
  elements.contractText.value = "";
  elements.contractId.value = "";
  clearSelectedFile({ focus: false });
  updateCharacterCount();
  switchInputMode("text");
}

async function submitReview() {
  if (state.reviewBusy) return;
  if (!canCreateReviews()) {
    showToast("当前账号为只读成员，不能新建合同审阅。", { error: true });
    window.location.hash = "#reviews";
    return;
  }
  clearInlineError(elements.reviewError);
  const contractId = elements.contractId.value.trim();
  let path;
  let options;
  if (state.inputMode === "text") {
    const text = elements.contractText.value.trim();
    if (!text) {
      showInlineError(elements.reviewError, "请先粘贴合同内容，或者点击“使用示例合同”。" );
      elements.contractText.focus();
      return;
    }
    path = "/reviews/text";
    options = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        contract_id: contractId || null,
        filename: "粘贴合同.txt",
        metadata: { source: "web_ui" },
      }),
    };
  } else {
    if (!state.selectedFile) {
      showInlineError(elements.reviewError, "请先选择一份合同文件。" );
      elements.chooseFileButton.focus();
      return;
    }
    const body = new FormData();
    body.append("file", state.selectedFile);
    if (contractId) body.append("contract_id", contractId);
    body.append("metadata", JSON.stringify({ source: "web_ui" }));
    path = "/reviews";
    options = { method: "POST", body };
  }

  state.reviewBusy = true;
  elements.reviewWait.hidden = false;
  elements.reviewButton.disabled = true;
  elements.reviewButton.textContent = "正在审阅……";
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REVIEW_TIMEOUT_MS);
  try {
    const payload = await request(path, { ...options, signal: controller.signal });
    const id = reviewId(payload);
    if (!id) throw new Error("服务已返回结果，但没有提供审阅编号。" );
    resetNewReviewForm();
    showToast("审阅已完成，正在打开结果。" );
    window.location.hash = `#review/${encodeURIComponent(id)}`;
  } catch (error) {
    const message =
      error?.name === "AbortError"
        ? "等待时间较长，请到“审阅记录”查看是否已经生成结果，或稍后重试。"
        : error?.message || "无法完成审阅，请稍后重试。";
    showInlineError(elements.reviewError, message);
    elements.reviewError.scrollIntoView({ block: "center" });
  } finally {
    window.clearTimeout(timeout);
    state.reviewBusy = false;
    elements.reviewWait.hidden = true;
    elements.reviewButton.disabled = false;
    elements.reviewButton.textContent = "开始审阅";
  }
}

async function handleChangePassword(event) {
  event.preventDefault();
  if (!elements.changePasswordForm.reportValidity()) return;
  clearInlineError(elements.passwordError);
  clearInlineSuccess(elements.passwordSuccess);
  const form = new FormData(elements.changePasswordForm);
  const currentPassword = String(form.get("current_password") || "");
  const newPassword = String(form.get("new_password") || "");
  const confirmation = String(form.get("confirm_password") || "");
  const policyError = passwordPolicyError(newPassword);
  if (policyError) {
    showInlineError(elements.passwordError, policyError);
    document.querySelector("#new-password")?.focus();
    return;
  }
  if (currentPassword === newPassword) {
    showInlineError(elements.passwordError, "新密码不能与当前密码相同。" );
    document.querySelector("#new-password")?.focus();
    return;
  }
  if (newPassword !== confirmation) {
    showInlineError(elements.passwordError, "两次输入的新密码不一致。" );
    document.querySelector("#confirm-password")?.focus();
    return;
  }

  const submit = elements.changePasswordForm.querySelector("button[type='submit']");
  setButtonBusy(submit, true, "正在更新……");
  try {
    const payload = await request("/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    elements.changePasswordForm.reset();
    showInlineSuccess(
      elements.passwordSuccess,
      payload?.message || "密码已修改，即将返回登录页面。",
    );
    window.setTimeout(() => {
      state.user = null;
      state.currentReview = null;
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
      showAuth("login");
      showToast("密码已修改，请使用新密码重新登录。" );
    }, 900);
  } catch (error) {
    showInlineError(elements.passwordError, error?.message || "密码修改失败，请检查当前密码。" );
  } finally {
    setButtonBusy(submit, false);
  }
}

function handleAdminForbidden(error) {
  elements.adminOnly.forEach((element) => {
    element.hidden = true;
  });
  elements.adminContent.hidden = true;
  showInlineError(
    elements.adminAccessError,
    error?.message === "你没有执行此操作的权限。"
      ? "当前账号没有成员与日志管理权限。权限可能已被组织管理员调整，你仍可继续使用账户和审阅记录。"
      : error?.message || "无法访问成员与日志，请联系组织所有者。",
  );
}

function createOption(value, label, selectedValue) {
  const option = createElement("option", "", label);
  option.value = value;
  option.selected = value === selectedValue;
  return option;
}

function renderMembers(items) {
  state.members = Array.isArray(items) ? items : [];
  elements.memberList.replaceChildren();
  if (state.members.length === 0) {
    elements.memberList.append(
      createElement("div", "empty-state", "当前组织还没有可显示的成员。"),
    );
    return;
  }

  state.members.forEach((member, index) => {
    const memberId = member.user_id || member.id || "";
    const card = createElement("article", "member-item");
    card.dataset.memberId = memberId;
    card.dataset.originalRole = member.role || "reviewer";
    card.dataset.originalStatus = member.status || "active";

    const header = createElement("div", "member-header");
    const heading = createElement("div", "member-heading");
    const titleLine = createElement("div", "member-title-line");
    titleLine.append(
      createElement("h3", "", member.display_name || member.email || "未命名成员"),
      createElement("span", "role-badge", ROLE_LABELS[member.role] || member.role || "角色未知"),
    );
    const status = createElement(
      "span",
      `member-status-badge${member.status === "disabled" ? " is-disabled" : ""}`,
      USER_STATUS_LABELS[member.status] || member.status || "状态未知",
    );
    const meta = createElement("p", "member-meta");
    meta.append(
      createElement("span", "", member.email || "邮箱未知"),
      createElement("span", "", `加入时间：${formatDate(member.created_at)}`),
    );
    if (memberId && memberId === state.user?.user_id) {
      meta.append(createElement("span", "", "当前账号"));
    }
    heading.append(titleLine, meta);
    header.append(heading, status);
    card.append(header);

    const controls = createElement("div", "member-controls");
    const roleField = createElement("div", "field-group");
    const roleLabel = createElement("label", "", "角色");
    const roleSelect = createElement("select", "");
    roleSelect.id = `member-role-${index}`;
    roleSelect.dataset.memberRole = "";
    if (member.role === "owner") {
      roleSelect.append(createOption("owner", "组织所有者", member.role));
    } else {
      roleSelect.append(
        createOption("admin", "管理员", member.role),
        createOption("reviewer", "审阅人", member.role),
        createOption("viewer", "只读成员", member.role),
      );
    }
    roleLabel.htmlFor = roleSelect.id;
    roleField.append(roleLabel, roleSelect);

    const statusField = createElement("div", "field-group");
    const statusLabel = createElement("label", "", "账号状态");
    const statusSelect = createElement("select", "");
    statusSelect.id = `member-status-${index}`;
    statusSelect.dataset.memberStatus = "";
    statusSelect.append(
      createOption("active", "正常", member.status),
      createOption("disabled", "禁用", member.status),
    );
    statusLabel.htmlFor = statusSelect.id;
    statusField.append(statusLabel, statusSelect);

    const save = createElement("button", "button button-secondary", "保存变更");
    save.type = "button";
    save.dataset.memberAction = "update";
    if (member.role === "owner") {
      roleSelect.disabled = true;
      statusSelect.disabled = true;
      save.disabled = true;
    }
    controls.append(roleField, statusField, save);
    card.append(controls);
    if (member.role === "owner") {
      card.append(
        createElement(
          "p",
          "member-protection-note",
          "组织所有者账号受保护；如需转移所有权，请通过专门的所有权转移流程处理。",
        ),
      );
    }
    const errorBox = createElement("div", "member-error");
    errorBox.setAttribute("role", "alert");
    errorBox.hidden = true;
    card.append(errorBox);
    elements.memberList.append(card);
  });
}

async function loadMembers() {
  if (!canManageMembers()) return;
  elements.membersLoading.hidden = false;
  elements.memberList.setAttribute("aria-busy", "true");
  clearInlineError(elements.membersError);
  try {
    const payload = await request("/users");
    renderMembers(payload?.items || []);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      handleAdminForbidden(error);
      return;
    }
    elements.memberList.replaceChildren();
    showInlineError(elements.membersError, error?.message || "组织成员加载失败，请稍后重试。" );
  } finally {
    elements.membersLoading.hidden = true;
    elements.memberList.removeAttribute("aria-busy");
  }
}

async function handleCreateMember(event) {
  event.preventDefault();
  if (!elements.memberCreateForm.reportValidity()) return;
  clearInlineError(elements.memberCreateError);
  clearInlineSuccess(elements.memberCreateSuccess);
  const form = new FormData(elements.memberCreateForm);
  const password = String(form.get("password") || "");
  const policyError = passwordPolicyError(password);
  if (policyError) {
    showInlineError(elements.memberCreateError, policyError);
    document.querySelector("#member-password")?.focus();
    return;
  }

  const submit = elements.memberCreateForm.querySelector("button[type='submit']");
  setButtonBusy(submit, true, "正在创建……");
  try {
    const payload = await request("/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        display_name: String(form.get("display_name") || "").trim(),
        email: String(form.get("email") || "").trim(),
        password,
        role: String(form.get("role") || "reviewer"),
      }),
    });
    elements.memberCreateForm.reset();
    document.querySelector("#member-role").value = "reviewer";
    showInlineSuccess(
      elements.memberCreateSuccess,
      `成员“${payload?.display_name || payload?.email || "新成员"}”已创建。`,
    );
    await loadMembers();
    void loadAuditLogs();
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      handleAdminForbidden(error);
      return;
    }
    showInlineError(elements.memberCreateError, error?.message || "成员创建失败，请检查填写内容。" );
  } finally {
    setButtonBusy(submit, false);
  }
}

async function updateMember(card, button) {
  const memberId = card.dataset.memberId;
  if (!memberId) return;
  const role = card.querySelector("[data-member-role]")?.value;
  const status = card.querySelector("[data-member-status]")?.value;
  const originalRole = card.dataset.originalRole;
  const originalStatus = card.dataset.originalStatus;
  const errorBox = card.querySelector(".member-error");
  errorBox.hidden = true;
  errorBox.textContent = "";
  if (originalRole === "owner" || role === "owner") {
    showToast("不能通过成员编辑转移或修改组织所有者。", { error: true });
    return;
  }
  if (role === originalRole && status === originalStatus) {
    showToast("没有需要保存的成员变更。" );
    return;
  }

  if (status !== originalStatus) {
    const disabling = status === "disabled" && status !== originalStatus;
    const confirmed = await confirmOperation({
      title: disabling
        ? "禁用这个成员账号？"
        : "重新启用这个成员账号？",
      message: disabling
        ? "禁用后，该成员的现有登录会话会失效，直到管理员重新启用账号。"
        : "重新启用后，该成员可以再次登录并按当前角色使用系统。",
      confirmText: disabling ? "确认禁用" : "确认启用",
      danger: disabling,
    });
    if (!confirmed) return;
  }

  const changes = {};
  if (role !== originalRole) changes.role = role;
  if (status !== originalStatus) changes.status = status;
  setButtonBusy(button, true, "正在保存……");
  try {
    const updated = await request(`/users/${encodeURIComponent(memberId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(changes),
    });
    showToast("成员权限和状态已更新。" );
    if (memberId === state.user?.user_id) {
      if (updated?.status === "disabled") {
        state.user = null;
        window.history.replaceState(null, "", window.location.pathname + window.location.search);
        showAuth("login");
        showToast("当前账号已被禁用，请联系组织所有者。", { error: true });
        return;
      }
      setUser(updated);
      if (!canManageMembers(updated)) {
        window.location.hash = "#account";
        showToast("你的角色已更新，成员管理入口已关闭。" );
        return;
      }
    }
    await loadMembers();
    void loadAuditLogs();
  } catch (error) {
    errorBox.textContent = error?.message || "成员更新失败，请稍后重试。";
    errorBox.hidden = false;
  } finally {
    setButtonBusy(button, false);
  }
}

function auditActionLabel(action) {
  return AUDIT_ACTION_LABELS[action] || action || "未知操作";
}

function renderAuditLogs(items) {
  elements.auditList.replaceChildren();
  const records = Array.isArray(items) ? items : [];
  if (records.length === 0) {
    elements.auditList.append(
      createElement("div", "empty-state", "当前还没有可显示的操作记录。"),
    );
    return;
  }
  const membersById = new Map(
    state.members.map((member) => [member.user_id || member.id, member.display_name || member.email]),
  );
  records.forEach((record) => {
    const item = createElement("article", "audit-item");
    item.append(createElement("time", "audit-time", formatDate(record.created_at)));
    const main = createElement("div", "audit-main");
    const actor = record.actor_user_id
      ? membersById.get(record.actor_user_id) || `成员 ${record.actor_user_id}`
      : "系统";
    const resource = [record.resource_type, record.resource_id].filter(Boolean).join(" · ");
    main.append(
      createElement("strong", "", auditActionLabel(record.action)),
      createElement("small", "", `${actor}${resource ? ` · ${resource}` : ""}`),
    );
    const outcome = createElement(
      "span",
      `audit-outcome${record.outcome === "success" ? "" : " is-failed"}`,
      record.outcome === "success" ? "成功" : record.outcome || "未知结果",
    );
    item.append(main, outcome);
    elements.auditList.append(item);
  });
}

async function loadAuditLogs() {
  if (!canManageMembers()) return;
  elements.auditLoading.hidden = false;
  elements.auditList.setAttribute("aria-busy", "true");
  clearInlineError(elements.auditError);
  try {
    const payload = await request("/audit-logs?page=1&page_size=50");
    renderAuditLogs(payload?.items || []);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      handleAdminForbidden(error);
      return;
    }
    elements.auditList.replaceChildren();
    showInlineError(elements.auditError, error?.message || "审计日志加载失败，请稍后重试。" );
  } finally {
    elements.auditLoading.hidden = true;
    elements.auditList.removeAttribute("aria-busy");
  }
}

async function logout() {
  const confirmed = await confirmOperation({
    title: "退出当前账号？",
    message: "退出后需要重新登录才能查看当前组织的合同审阅记录。",
    confirmText: "确认退出",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await request("/auth/logout", { method: "POST" });
    state.user = null;
    state.currentReview = null;
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
    showAuth("login");
    showToast("已安全退出。" );
  } catch (error) {
    showToast(error?.message || "退出失败，请稍后重试。", { error: true });
  }
}

elements.loginForm.addEventListener("submit", handleLogin);
elements.registerForm.addEventListener("submit", handleRegistration);
elements.authSwitch.addEventListener("click", () => {
  setAuthMode(state.authMode === "login" ? "register" : "login");
});
elements.logoutButton.addEventListener("click", logout);
elements.mobileLogoutButton.addEventListener("click", logout);
window.addEventListener("hashchange", handleRoute);
elements.changePasswordForm.addEventListener("submit", handleChangePassword);
elements.memberCreateForm.addEventListener("submit", handleCreateMember);
elements.refreshMembers.addEventListener("click", () => void loadMembers());
elements.refreshAudit.addEventListener("click", () => void loadAuditLogs());
elements.memberList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-member-action='update']");
  if (!button) return;
  const card = button.closest(".member-item");
  if (card) void updateMember(card, button);
});

elements.reviewFilterForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.reviewFilters = {
    q: elements.reviewSearch.value.trim(),
    status: elements.reviewStatus.value,
    includeDeleted: elements.includeDeleted.checked,
  };
  state.reviewPage = 1;
  void loadReviewList();
});

elements.workFilterForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.workFilters = {
    kind: elements.workKind.value,
    status: elements.workStatus.value,
    assignee: elements.workAssignee.value,
    overdue: elements.workOverdue.checked,
  };
  state.workPage = 1;
  void loadWorkItems();
});

elements.workKind.addEventListener("change", populateWorkStatusFilter);

elements.clearWorkFilters.addEventListener("click", () => {
  elements.workKind.value = "";
  populateWorkStatusFilter();
  elements.workStatus.value = "";
  elements.workAssignee.value = "";
  elements.workOverdue.checked = false;
  state.workFilters = { kind: "", status: "", assignee: "", overdue: false };
  state.workPage = 1;
  void loadWorkItems();
});

elements.workPreviousPage.addEventListener("click", () => {
  if (state.workPage <= 1) return;
  state.workPage -= 1;
  void loadWorkItems();
});

elements.workNextPage.addEventListener("click", () => {
  if (state.workPage >= state.workPages) return;
  state.workPage += 1;
  void loadWorkItems();
});

function handleWorkItemOpen(event) {
  const button = event.target.closest("button[data-work-item-action='open']");
  if (!button) return false;
  void openWorkItem(button.dataset.workItemId, button);
  return true;
}

elements.workItemList.addEventListener("click", handleWorkItemOpen);
elements.obligationList.addEventListener("click", handleWorkItemOpen);
elements.decisionForm.addEventListener("submit", submitDecision);
elements.decisionTarget.addEventListener("change", updateDecisionSubmitLabel);

elements.clearReviewFilters.addEventListener("click", () => {
  elements.reviewSearch.value = "";
  elements.reviewStatus.value = "";
  elements.includeDeleted.checked = false;
  state.reviewFilters = { q: "", status: "", includeDeleted: false };
  state.reviewPage = 1;
  void loadReviewList();
});

elements.previousPage.addEventListener("click", () => {
  if (state.reviewPage <= 1) return;
  state.reviewPage -= 1;
  void loadReviewList();
});

elements.nextPage.addEventListener("click", () => {
  if (state.reviewPage >= state.reviewPages) return;
  state.reviewPage += 1;
  void loadReviewList();
});

elements.reviewList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-review-action]");
  if (!button) return;
  const id = button.dataset.reviewId;
  const title = button.dataset.reviewTitle || "这条审阅记录";
  if (button.dataset.reviewAction === "delete") void deleteReview(id, title);
  if (button.dataset.reviewAction === "restore") void restoreReview(id, title);
});

elements.deleteReviewButton.addEventListener("click", () => {
  if (!state.currentReviewId || !state.currentReview) return;
  void deleteReview(state.currentReviewId, reviewTitle(state.currentReview), { fromDetail: true });
});

elements.restoreReviewButton.addEventListener("click", () => {
  if (!state.currentReviewId || !state.currentReview) return;
  void restoreReview(state.currentReviewId, reviewTitle(state.currentReview), { fromDetail: true });
});

elements.tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => switchInputMode(tab.dataset.mode));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let nextIndex = index;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % elements.tabs.length;
    if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + elements.tabs.length) % elements.tabs.length;
    }
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = elements.tabs.length - 1;
    switchInputMode(elements.tabs[nextIndex].dataset.mode, { focus: true });
  });
});

elements.contractText.addEventListener("input", updateCharacterCount);
elements.sampleButton.addEventListener("click", () => {
  switchInputMode("text");
  elements.contractText.value = SAMPLE_CONTRACT;
  updateCharacterCount();
  elements.contractText.focus();
});
elements.chooseFileButton.addEventListener("click", () => elements.contractFile.click());
elements.contractFile.addEventListener("change", () => selectFile(elements.contractFile.files?.[0]));
elements.removeFileButton.addEventListener("click", () => clearSelectedFile());

["dragenter", "dragover"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("is-dragging");
  });
});
["dragleave", "drop"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("is-dragging");
  });
});
elements.dropZone.addEventListener("drop", (event) => selectFile(event.dataTransfer?.files?.[0]));
elements.reviewButton.addEventListener("click", submitReview);

elements.riskFilters.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-risk]");
  if (!button) return;
  state.activeRisk = button.dataset.risk;
  updateRiskFilterControls(state.activeRisk);
  renderFindings(state.reportFindings);
});

elements.findingList.addEventListener("click", (event) => {
  if (handleWorkItemOpen(event)) return;
  const button = event.target.closest("button[data-finding-action]");
  if (!button) return;
  const card = button.closest(".finding-card");
  if (!card) return;
  if (button.dataset.findingAction === "copy") {
    void copyFindingRecommendation(card, button);
  } else if (button.dataset.findingAction === "feedback") {
    void submitFindingFeedback(card, button, button.dataset.accepted === "true");
  }
});

elements.workItemForm.addEventListener("submit", saveWorkItem);
elements.workItemClose.addEventListener("click", closeWorkItemDialog);
elements.workItemCancel.addEventListener("click", closeWorkItemDialog);
elements.workItemDialog.addEventListener("close", () => {
  state.workItemRequestVersion += 1;
  const target = state.workItemReturnFocus;
  state.currentWorkItem = null;
  state.workItemReturnFocus = null;
  if (target instanceof HTMLElement && target.isConnected) target.focus();
});

elements.confirmDialog.addEventListener("close", () => {
  const resolve = state.pendingConfirm;
  state.pendingConfirm = null;
  if (resolve) resolve(elements.confirmDialog.returnValue === "confirm");
});

updateCharacterCount();
void initialize();
