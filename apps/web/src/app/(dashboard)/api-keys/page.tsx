"use client";

import { useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { ApiKey } from "@/types";

const defaultForm = {
  name: "",
  token_limit: "",
  request_limit: "",
  budget_limit: "",
};

type LimitMode = "unlimited" | "limited";
type ModalMode = "create" | "edit";

function formatDate(value: string | null) {
  if (!value) {
    return "暂无记录";
  }

  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatLimit(value: number | string | null) {
  if (value === null || value === "" || value === undefined) {
    return "无限制";
  }
  return `${value}`;
}

function formatUsagePercent(used: number, limit: number | null) {
  if (!limit || limit <= 0) {
    return Math.min(used > 0 ? 12 : 0, 100);
  }
  return Math.min(Math.round((used / limit) * 100), 100);
}

function maskKey(prefix: string) {
  return `${prefix}${"•".repeat(18)}`;
}

function EyeIcon() {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24">
      <path
        d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24">
      <rect
        height="14"
        rx="2"
        stroke="currentColor"
        strokeWidth="2"
        width="14"
        x="8"
        y="6"
      />
      <path
        d="M16 4H6a2 2 0 0 0-2 2v10"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path
        d="M12 20h9"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <path
        d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path
        d="M3 6h18"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <path
        d="M8 6V4h8v2"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <path
        d="M19 6l-1 14H6L5 6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <path
        d="M10 11v6M14 11v6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  );
}

export default function ApiKeysPage() {
  const [items, setItems] = useState<ApiKey[]>([]);
  const [form, setForm] = useState(defaultForm);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [limitMode, setLimitMode] = useState<LimitMode>("unlimited");
  const [modalMode, setModalMode] = useState<ModalMode>("create");
  const [editingItem, setEditingItem] = useState<ApiKey | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [visibleId, setVisibleId] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  const [deletingItem, setDeletingItem] = useState<ApiKey | null>(null);

  const hasLimits = useMemo(
    () =>
      Boolean(
        form.token_limit.trim() || form.request_limit.trim() || form.budget_limit.trim(),
      ),
    [form.budget_limit, form.request_limit, form.token_limit],
  );

  async function load() {
    const result = await apiFetch<ApiKey[]>("/api-keys");
    setItems(result);
  }

  useEffect(() => {
    let active = true;
    void apiFetch<ApiKey[]>("/api-keys").then((result) => {
      if (active) {
        setItems(result);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!notice) {
      return;
    }

    const timer = window.setTimeout(() => setNotice(""), 2200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  function openCreateModal() {
    setModalMode("create");
    setEditingItem(null);
    setForm(defaultForm);
    setLimitMode("unlimited");
    setIsSubmitting(false);
    setErrorMessage("");
    setIsModalOpen(true);
  }

  function openEditModal(item: ApiKey) {
    setModalMode("edit");
    setEditingItem(item);
    setForm({
      name: item.name,
      token_limit: item.token_limit ? String(item.token_limit) : "",
      request_limit: item.request_limit ? String(item.request_limit) : "",
      budget_limit: item.budget_limit ? String(item.budget_limit) : "",
    });
    setLimitMode(item.token_limit || item.request_limit || item.budget_limit ? "limited" : "unlimited");
    setIsSubmitting(false);
    setErrorMessage("");
    setIsModalOpen(true);
  }

  function closeModal() {
    setIsModalOpen(false);
    setIsSubmitting(false);
    setErrorMessage("");
    setEditingItem(null);
    setForm(defaultForm);
    setLimitMode("unlimited");
  }

  async function handleSubmit() {
    if (!form.name.trim()) {
      setErrorMessage("请输入密钥名称");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      if (modalMode === "create") {
        await apiFetch<ApiKey>("/api-keys", {
          method: "POST",
          body: JSON.stringify({
            name: form.name.trim(),
            token_limit:
              limitMode === "limited" && form.token_limit ? Number(form.token_limit) : null,
            request_limit:
              limitMode === "limited" && form.request_limit ? Number(form.request_limit) : null,
            budget_limit:
              limitMode === "limited" && form.budget_limit ? Number(form.budget_limit) : null,
          }),
        });
      } else if (editingItem) {
        await apiFetch<ApiKey>(`/api-keys/${editingItem.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            name: form.name.trim(),
            token_limit:
              limitMode === "limited" && form.token_limit ? Number(form.token_limit) : null,
            request_limit:
              limitMode === "limited" && form.request_limit ? Number(form.request_limit) : null,
            budget_limit:
              limitMode === "limited" && form.budget_limit ? Number(form.budget_limit) : null,
          }),
        });
      }

      closeModal();
      await load();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "操作失败");
      setIsSubmitting(false);
    }
  }

  async function toggleStatus(item: ApiKey) {
    await apiFetch(`/api-keys/${item.id}/${item.status === "active" ? "disable" : "enable"}`, {
      method: "POST",
    });
    await load();
  }

  async function deleteItem(item: ApiKey) {
    await apiFetch(`/api-keys/${item.id}`, { method: "DELETE" });
    await load();
    setDeletingItem(null);
    setNotice("API 密钥已删除。");
  }

  async function copyKey(item: ApiKey) {
    if (!item.plaintext_key) {
      setNotice("这条旧密钥没有明文备份，重新创建后即可长期显示和复制。");
      return;
    }

    try {
      await navigator.clipboard.writeText(item.plaintext_key);
      setNotice("API 密钥已复制。");
    } catch {
      setNotice("复制失败，请检查浏览器权限。");
    }
  }

  function toggleReveal(item: ApiKey) {
    if (!item.plaintext_key) {
      setNotice("这条旧密钥没有明文备份，重新创建后即可长期显示和复制。");
      return;
    }

    setVisibleId(visibleId === item.id ? null : item.id);
  }

  return (
    <>
      {notice ? (
        <div className="fixed right-6 top-6 z-[60] rounded-2xl border border-[#d7e3ff] bg-white px-4 py-3 text-sm text-[#315efb] shadow-[0_16px_40px_rgba(16,24,40,0.14)]">
          {notice}
        </div>
      ) : null}

      <div className="space-y-5">
        <Panel
          title="API密钥管理"
          subtitle="创建并管理访问密钥，可按需限制 Token、请求次数和预算。"
          action={
            <button
              className="rounded-2xl bg-[var(--brand)] px-5 py-3 text-white transition hover:opacity-95"
              onClick={openCreateModal}
              type="button"
            >
              + 创建新密钥
            </button>
          }
        >
          <div className="rounded-3xl border border-dashed border-[var(--line)] bg-[var(--page-bg)] px-6 py-8 text-center text-[var(--text-muted)]">
            点击右上角“创建新密钥”开始创建 API 密钥。新创建的密钥支持长期显示和复制。
          </div>
        </Panel>

        {items.map((item) => {
          const tokenPercent = formatUsagePercent(item.used_tokens, item.token_limit);
          const requestPercent = formatUsagePercent(item.used_requests, item.request_limit);
          const keyText =
            visibleId === item.id && item.plaintext_key
              ? item.plaintext_key
              : maskKey(item.key_prefix);

          return (
            <section
              key={item.id}
              className="rounded-[24px] border border-[var(--line)] bg-white p-6 shadow-[var(--card-shadow)]"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-[18px] font-semibold text-[#172033]">{item.name}</h2>
                  <div className="mt-1.5 text-[14px] text-[var(--text-muted)]">
                    创建于 {formatDate(item.created_at)}
                  </div>
                </div>
                <button
                  className={`rounded-full px-3.5 py-1.5 text-[13px] font-semibold ${
                    item.status === "active"
                      ? "bg-[#dcf8e7] text-[#19984c]"
                      : "bg-[#f1f3f7] text-[#667085]"
                  }`}
                  onClick={() => void toggleStatus(item)}
                  type="button"
                >
                  {item.status === "active" ? "活跃" : "已停用"}
                </button>
              </div>

              <div className="mt-5">
                <div className="mb-2.5 text-[14px] font-semibold text-[#3d4859]">API密钥</div>
                <div className="flex items-center gap-3">
                  <div className="flex min-h-[60px] flex-1 items-center rounded-[16px] border border-[#ccd5e3] bg-[#fafbfc] px-5 text-[16px] tracking-[0.12em] text-[#172033]">
                    {keyText}
                  </div>
                  <button
                    className="rounded-xl p-2 text-[#7b8495] transition hover:bg-[#f3f6fb] hover:text-[#315efb]"
                    onClick={() => toggleReveal(item)}
                    type="button"
                  >
                    <EyeIcon />
                  </button>
                  <button
                    className="rounded-xl p-2 text-[#7b8495] transition hover:bg-[#f3f6fb] hover:text-[#315efb]"
                    onClick={() => void copyKey(item)}
                    type="button"
                  >
                    <CopyIcon />
                  </button>
                </div>
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div className="rounded-[20px] bg-[#f7f9fc] p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[15px] font-semibold text-[#3d4859]">Token用量</div>
                    <div className="text-[15px] text-[#667085]">
                      {item.used_tokens.toLocaleString()} / {item.token_limit?.toLocaleString() ?? "无限制"}
                    </div>
                  </div>
                  <div className="mt-4 h-3 overflow-hidden rounded-full bg-[#e5e7eb]">
                    <div
                      className="h-full rounded-full bg-[#315efb]"
                      style={{ width: `${tokenPercent}%` }}
                    />
                  </div>
                  <div className="mt-2.5 text-[14px] text-[#667085]">已使用 {tokenPercent}%</div>
                </div>

                <div className="rounded-[20px] bg-[#f7f9fc] p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[15px] font-semibold text-[#3d4859]">请求次数</div>
                    <div className="text-[15px] text-[#667085]">
                      {item.used_requests.toLocaleString()} / {item.request_limit?.toLocaleString() ?? "无限制"}
                    </div>
                  </div>
                  <div className="mt-4 h-3 overflow-hidden rounded-full bg-[#e5e7eb]">
                    <div
                      className="h-full rounded-full bg-[#16a34a]"
                      style={{ width: `${requestPercent}%` }}
                    />
                  </div>
                  <div className="mt-2.5 text-[14px] text-[#667085]">已使用 {requestPercent}%</div>
                </div>
              </div>

              <div className="mt-5 rounded-[20px] bg-[#f7f9fc] p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="text-[15px] font-semibold text-[#172033]">限额</div>
                  <button
                    className="text-[14px] font-semibold text-[#315efb] transition hover:opacity-80"
                    onClick={() => openEditModal(item)}
                    type="button"
                  >
                    设置
                  </button>
                </div>
                <div className="mt-4 grid gap-3 text-[14px] text-[#667085] md:grid-cols-[1fr_auto]">
                  <div className="space-y-3">
                    <div>Token限额</div>
                    <div>请求限额</div>
                    <div>预算限额</div>
                  </div>
                  <div className="space-y-3 text-right text-[#172033]">
                    <div>{formatLimit(item.token_limit?.toLocaleString() ?? null)}</div>
                    <div>{formatLimit(item.request_limit?.toLocaleString() ?? null)}</div>
                    <div>{item.budget_limit ? `¥${item.budget_limit}` : "无限制"}</div>
                  </div>
                </div>
              </div>

              <div className="mt-5 grid gap-5 md:grid-cols-2">
                <div>
                  <div className="text-[15px] font-semibold text-[#3d4859]">最后使用时间</div>
                  <div className="mt-2 text-[14px] text-[#4d596a]">{formatDate(item.last_used_at)}</div>
                </div>
                <div>
                  <div className="text-[15px] font-semibold text-[#3d4859]">状态</div>
                  <div className="mt-2 flex items-center gap-3 text-[14px] text-[#4d596a]">
                    <span
                      className={`h-3 w-3 rounded-full ${
                        item.status === "active" ? "bg-[#22c55e]" : "bg-[#9ca3af]"
                      }`}
                    />
                    {item.status === "active" ? "活跃" : "已停用"}
                  </div>
                </div>
              </div>

              <div className="mt-5 flex items-center justify-end gap-5">
                <button
                  className="flex items-center gap-2 text-[15px] font-semibold text-[#315efb]"
                  onClick={() => openEditModal(item)}
                  type="button"
                >
                  <EditIcon />
                  编辑
                </button>
                <button
                  className="flex items-center gap-2 text-[15px] font-semibold text-[#ef4444]"
                  onClick={() => setDeletingItem(item)}
                  type="button"
                >
                  <TrashIcon />
                  删除
                </button>
              </div>

              <div className="mt-6 rounded-[24px] bg-[#eef4ff] p-6">
                <div className="text-[18px] font-semibold text-[#172033]">API使用信息</div>
                <div className="mt-5 grid gap-4 md:grid-cols-3">
                  <div className="rounded-[18px] bg-white px-6 py-5">
                    <div className="text-[16px] font-semibold text-[#315efb]">
                      {item.month_requests.toLocaleString()}
                    </div>
                    <div className="mt-2 text-[14px] text-[#667085]">本月请求数</div>
                  </div>
                  <div className="rounded-[18px] bg-white px-6 py-5">
                    <div className="text-[16px] font-semibold text-[#16a34a]">
                      {Number(item.success_rate).toFixed(1)}%
                    </div>
                    <div className="mt-2 text-[14px] text-[#667085]">成功率</div>
                  </div>
                  <div className="rounded-[18px] bg-white px-6 py-5">
                    <div className="text-[16px] font-semibold text-[#9333ea]">
                      {item.avg_response_time_ms ? `${(item.avg_response_time_ms / 1000).toFixed(1)}s` : "--"}
                    </div>
                    <div className="mt-2 text-[14px] text-[#667085]">平均响应时间</div>
                  </div>
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#101828]/45 px-4 py-8">
          <div className="w-full max-w-[680px] overflow-hidden rounded-[24px] bg-white shadow-[0_24px_70px_rgba(16,24,40,0.16)]">
            <div className="flex items-center justify-between border-b border-[#dde3ef] px-8 py-7">
              <h2 className="text-[22px] font-semibold tracking-tight text-[#172033]">
                {modalMode === "create" ? "创建 API 密钥" : "编辑 API 密钥"}
              </h2>
              <button
                aria-label="关闭"
                className="text-[42px] leading-none text-[#a0a9ba] transition hover:text-[#6b7380]"
                onClick={closeModal}
                type="button"
              >
                ×
              </button>
            </div>

            <div className="space-y-7 px-8 py-8 text-[#4d596a]">
              <p className="max-w-3xl text-[16px] leading-8">
                创建一个新的 API 密钥来访问 API，您可以设置使用上限来控制成本。
              </p>

              <div className="space-y-4">
                <label className="block text-[16px] font-semibold text-[#172033]" htmlFor="api-key-name">
                  名称
                </label>
                <input
                  id="api-key-name"
                  className="h-[58px] w-full rounded-[16px] border border-[#ccd5e3] px-5 text-[16px] text-[#172033] outline-none transition placeholder:text-[#b1b8c5] focus:border-[#2f6df6]"
                  placeholder="我的 API 密钥"
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                />
              </div>

              <div className="space-y-4">
                <div className="text-[16px] font-semibold text-[#172033]">使用上限</div>
                <label className="flex cursor-pointer items-center gap-3 text-[16px] font-medium text-[#3d4859]">
                  <span
                    className={`flex h-7 w-7 items-center justify-center rounded-full border-2 ${
                      limitMode === "unlimited" ? "border-[#1677ff]" : "border-[#7f8795]"
                    }`}
                  >
                    <span
                      className={`h-4 w-4 rounded-full ${
                        limitMode === "unlimited" ? "bg-[#1677ff]" : "bg-transparent"
                      }`}
                    />
                  </span>
                  <input
                    checked={limitMode === "unlimited"}
                    className="sr-only"
                    name="limitMode"
                    onChange={() => setLimitMode("unlimited")}
                    type="radio"
                  />
                  无限制
                </label>

                <label className="flex cursor-pointer items-center gap-3 text-[16px] font-medium text-[#3d4859]">
                  <span
                    className={`flex h-7 w-7 items-center justify-center rounded-full border-2 ${
                      limitMode === "limited" ? "border-[#1677ff]" : "border-[#7f8795]"
                    }`}
                  >
                    <span
                      className={`h-4 w-4 rounded-full ${
                        limitMode === "limited" ? "bg-[#1677ff]" : "bg-transparent"
                      }`}
                    />
                  </span>
                  <input
                    checked={limitMode === "limited"}
                    className="sr-only"
                    name="limitMode"
                    onChange={() => setLimitMode("limited")}
                    type="radio"
                  />
                  限制使用量
                </label>

                {limitMode === "limited" ? (
                  <div className="grid gap-4 pt-2 md:grid-cols-3">
                    <input
                      className="h-[52px] rounded-[14px] border border-[#ccd5e3] px-4 text-[15px] text-[#172033] outline-none transition placeholder:text-[#b1b8c5] focus:border-[#2f6df6]"
                      inputMode="numeric"
                      placeholder="Token 限额"
                      value={form.token_limit}
                      onChange={(event) => setForm({ ...form, token_limit: event.target.value })}
                    />
                    <input
                      className="h-[52px] rounded-[14px] border border-[#ccd5e3] px-4 text-[15px] text-[#172033] outline-none transition placeholder:text-[#b1b8c5] focus:border-[#2f6df6]"
                      inputMode="numeric"
                      placeholder="请求次数限额"
                      value={form.request_limit}
                      onChange={(event) => setForm({ ...form, request_limit: event.target.value })}
                    />
                    <input
                      className="h-[52px] rounded-[14px] border border-[#ccd5e3] px-4 text-[15px] text-[#172033] outline-none transition placeholder:text-[#b1b8c5] focus:border-[#2f6df6]"
                      inputMode="decimal"
                      placeholder="预算限额（元）"
                      value={form.budget_limit}
                      onChange={(event) => setForm({ ...form, budget_limit: event.target.value })}
                    />
                  </div>
                ) : null}
              </div>

              {errorMessage ? (
                <div className="rounded-2xl border border-[#ffd2d2] bg-[#fff4f4] px-5 py-4 text-base text-[#c43131]">
                  {errorMessage}
                </div>
              ) : null}
            </div>

            <div className="flex items-center justify-end gap-4 px-8 pb-8">
              <button
                className="rounded-[14px] border border-[#cfd6e2] bg-white px-7 py-3.5 text-[16px] font-semibold text-[#3e4858] transition hover:bg-[#f7f9fc]"
                onClick={closeModal}
                type="button"
              >
                取消
              </button>
              <button
                className="rounded-[14px] bg-[#0a0a0a] px-7 py-3.5 text-[16px] font-semibold text-white transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isSubmitting || !form.name.trim() || (limitMode === "limited" && !hasLimits)}
                onClick={() => void handleSubmit()}
                type="button"
              >
                {isSubmitting ? "提交中..." : modalMode === "create" ? "创建 API 密钥" : "保存修改"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {deletingItem ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-[#101828]/45 px-4">
          <div className="w-full max-w-[480px] rounded-[24px] bg-white p-7 shadow-[0_24px_70px_rgba(16,24,40,0.16)]">
            <h3 className="text-[22px] font-semibold text-[#172033]">确认删除 API 密钥</h3>
            <p className="mt-4 text-[15px] leading-7 text-[#667085]">
              删除后将无法继续使用该密钥，历史调用记录会保留。确认删除“{deletingItem.name}”吗？
            </p>
            <div className="mt-7 flex justify-end gap-3">
              <button
                className="rounded-[14px] border border-[#cfd6e2] bg-white px-5 py-3 text-[15px] font-semibold text-[#3e4858]"
                onClick={() => setDeletingItem(null)}
                type="button"
              >
                取消
              </button>
              <button
                className="rounded-[14px] bg-[#ef4444] px-5 py-3 text-[15px] font-semibold text-white"
                onClick={() => void deleteItem(deletingItem)}
                type="button"
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
