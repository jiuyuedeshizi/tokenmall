"use client";

import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminUsage, PaginatedResponse } from "@/types";

function formatBillingSource(value?: string) {
  if (value === "provider_usage") {
    return "官方 usage";
  }
  if (value === "estimated_stream") {
    return "流式估算";
  }
  if (value === "error") {
    return "错误回滚";
  }
  if (value === "reserved_estimate") {
    return "预扣估算";
  }
  return value || "未标记";
}

export default function AdminUsagePage() {
  const [items, setItems] = useState<AdminUsage[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  useEffect(() => {
    let active = true;
    void apiFetch<PaginatedResponse<AdminUsage>>(`/admin/usage?page=${page}&page_size=${pageSize}`).then((result) => {
      if (active) {
        setItems(result.items);
        setTotal(result.total);
      }
    });
    return () => {
      active = false;
    };
  }, [page]);

  return (
    <AuthGuard>
      {({ user }) => (
        <AdminShell user={user}>
          <Panel title="使用记录" subtitle="查看全平台调用记录、用量与错误。">
            <div className="space-y-4">
              {items.map((item) => (
                <div key={item.id} className="rounded-[24px] border border-[#dbe3ef] px-5 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-semibold text-[#172033]">
                        {item.user_name} / {item.model_code}
                      </div>
                      <div className="mt-1 text-sm text-[#667085]">{item.user_email}</div>
                      <div className="mt-1 text-sm text-[#667085]">
                        request_id: {item.request_id}
                      </div>
                    </div>
                    <div className="text-right text-sm text-[#667085]">
                      <div>{new Date(item.created_at).toLocaleString("zh-CN")}</div>
                      <div className="mt-1">{item.status}</div>
                      <div className="mt-1">{formatBillingSource(item.billing_source)}</div>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 text-sm text-[#4d596a] md:grid-cols-4">
                    <div>输入: {item.input_tokens}</div>
                    <div>输出: {item.output_tokens}</div>
                    <div>总量: {item.total_tokens}</div>
                    <div>费用: ¥{item.amount}</div>
                  </div>
                  {item.error_message ? (
                    <div className="mt-4 rounded-[16px] bg-[#fff7f7] px-4 py-3 text-sm text-[#b42318]">
                      {item.error_message}
                    </div>
                  ) : null}
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
