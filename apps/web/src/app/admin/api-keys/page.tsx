"use client";

import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminApiKey, PaginatedResponse } from "@/types";

function formatKeyStatus(status: string) {
  if (status === "active") {
    return "启用中";
  }
  if (status === "disabled") {
    return "已禁用";
  }
  if (status === "arrears") {
    return "欠费";
  }
  if (status === "quota_exceeded") {
    return "额度超限";
  }
  return status;
}

export default function AdminApiKeysPage() {
  const [items, setItems] = useState<AdminApiKey[]>([]);
  const [notice, setNotice] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  async function load() {
    const result = await apiFetch<PaginatedResponse<AdminApiKey>>(`/admin/api-keys?page=${page}&page_size=${pageSize}`);
    setItems(result.items);
    setTotal(result.total);
  }

  useEffect(() => {
    let active = true;
    void apiFetch<PaginatedResponse<AdminApiKey>>(`/admin/api-keys?page=${page}&page_size=${pageSize}`).then((result) => {
      if (active) {
        setItems(result.items);
        setTotal(result.total);
      }
    });
    return () => {
      active = false;
    };
  }, [page]);

  useEffect(() => {
    if (!notice) {
      return;
    }
    const timer = window.setTimeout(() => setNotice(""), 2200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  return (
    <AuthGuard>
      {({ user }) => (
        <AdminShell user={user}>
          {notice ? (
            <div className="fixed right-8 top-24 z-50 rounded-full bg-[#172033] px-4 py-2 text-[14px] text-white shadow-lg">
              {notice}
            </div>
          ) : null}
          <Panel title="API Key 管理" subtitle="查看全局 Key 状态、所属用户与额度消耗，并支持启停和删除。">
            <div className="space-y-4">
              {items.map((item) => (
                <div key={item.id} className="rounded-[24px] border border-[#dbe3ef] px-5 py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{item.name}</div>
                      <div className="mt-1 text-sm text-[#667085]">{item.key_prefix}</div>
                      <div className="mt-1 text-sm text-[#667085]">
                        {item.user_name} / {item.user_email}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span>{formatKeyStatus(item.status)}</span>
                      <button
                        className="rounded-full border border-[#dbe3ef] px-3 py-1 text-sm"
                        onClick={() =>
                          void apiFetch(`/admin/api-keys/${item.id}/${item.status === "active" ? "disable" : "enable"}`, {
                            method: "POST",
                          })
                            .then(async () => {
                              setNotice(item.status === "active" ? "API Key 已禁用" : "API Key 已启用");
                              await load();
                            })
                            .catch((error) => {
                              setNotice(error instanceof Error ? error.message : "操作失败");
                            })
                        }
                        type="button"
                      >
                        {item.status === "active" ? "禁用" : "启用"}
                      </button>
                      <button
                        className="rounded-full border border-[#ef4444] px-3 py-1 text-sm text-[#ef4444]"
                        onClick={() =>
                          void apiFetch(`/admin/api-keys/${item.id}`, { method: "DELETE" })
                            .then(async () => {
                              setNotice("API Key 已删除");
                              await load();
                            })
                            .catch((error) => {
                              setNotice(error instanceof Error ? error.message : "删除失败");
                            })
                        }
                        type="button"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 text-sm text-[#667085] md:grid-cols-3">
                    <div>Token: {item.used_tokens} / {item.token_limit ?? "不限"}</div>
                    <div>请求: {item.used_requests} / {item.request_limit ?? "不限"}</div>
                    <div>预算: ¥{item.used_amount} / {item.budget_limit ?? "不限"}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-5 flex items-center justify-between">
              <div className="text-[14px] text-[#667085]">
                共 {total} 条，当前第 {page} / {totalPages} 页
              </div>
              <div className="flex items-center gap-3">
                <button
                  className="rounded-[14px] border border-[#d8e0eb] px-4 py-2 text-[14px] font-semibold text-[#172033] disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={page <= 1}
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  type="button"
                >
                  上一页
                </button>
                <button
                  className="rounded-[14px] border border-[#d8e0eb] px-4 py-2 text-[14px] font-semibold text-[#172033] disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={page >= totalPages}
                  onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                  type="button"
                >
                  下一页
                </button>
              </div>
            </div>
          </Panel>
        </AdminShell>
      )}
    </AuthGuard>
  );
}
