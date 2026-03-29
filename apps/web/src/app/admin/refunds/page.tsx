"use client";

import { useCallback, useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminRefund, AdminRefundActionResult, PaginatedResponse } from "@/types";

function formatRefundStatus(status: string) {
  if (status === "refunded" || status === "approved") {
    return { label: "已退款", color: "text-[#22c55e]" };
  }
  if (status === "rejected") {
    return { label: "已拒绝", color: "text-[#ef4444]" };
  }
  if (status === "processing") {
    return { label: "部分退款", color: "text-[#f59e0b]" };
  }
  return { label: "处理中", color: "text-[#eab308]" };
}

export default function AdminRefundsPage() {
  const [items, setItems] = useState<AdminRefund[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [notice, setNotice] = useState("");
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const loadData = useCallback(async (targetPage: number) => {
    const result = await apiFetch<PaginatedResponse<AdminRefund>>(
      `/admin/refunds?page=${targetPage}&page_size=${pageSize}`,
    );
    setItems(result.items);
    setTotal(result.total);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadData(page);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [page, loadData]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 2200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  async function updateRefund(refundId: number, action: "approve" | "reject") {
    try {
      const result = await apiFetch<AdminRefundActionResult>(`/admin/refunds/${refundId}/${action}`, { method: "POST" });
      if (action === "approve") {
        setNotice(result.message || (result.status === "refunded" ? "退款已处理完成" : "退款处理中，请稍后查询渠道结果"));
      } else {
        setNotice("退款申请已拒绝");
      }
      await loadData(page);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "处理退款失败");
    }
  }

  return (
    <AuthGuard>
      {({ user }) => (
        <AdminShell user={user}>
          <div className="mx-auto max-w-[1160px]">
            <Panel title="退款管理" subtitle="审核用户提交的退款申请，并完成退款处理。">
              {notice ? (
                <div className="mb-5 rounded-[16px] bg-[#172033] px-4 py-3 text-[14px] text-white">{notice}</div>
              ) : null}
              <div className="space-y-3.5">
                {items.map((item) => {
                  const status = formatRefundStatus(item.status);
                  return (
                    <div key={item.request_no} className="rounded-[18px] border border-[#dbe3ef] bg-white px-5 py-4">
                      <div className="flex items-start justify-between gap-5">
                        <div className="min-w-0 flex-1 space-y-1.5">
                          <div className="flex flex-wrap items-center gap-2.5">
                            <div className="text-[17px] font-semibold text-[#172033]">{item.user_name}</div>
                            <div className="text-[13px] text-[#667085]">{item.user_email}</div>
                          </div>
                          <div className="grid gap-1.5 text-[13px] text-[#667085] md:grid-cols-2">
                            <div>申请单号：{item.request_no}</div>
                            <div>申请时间：{new Date(item.created_at).toLocaleString("zh-CN")}</div>
                            <div>已退金额：¥{item.refunded_amount ?? "0.00"}</div>
                            <div>剩余金额：¥{item.remaining_amount ?? item.amount}</div>
                            <div className="md:col-span-2">退款理由：{item.reason || "申请退款"}</div>
                            {item.admin_note ? <div className="md:col-span-2">处理说明：{item.admin_note}</div> : null}
                          </div>
                        </div>
                        <div className="min-w-[154px] text-right">
                          <div className="text-[22px] font-semibold text-[#172033]">¥{item.amount}</div>
                          <div className={`mt-1 text-[15px] font-semibold ${status.color}`}>{status.label}</div>
                        </div>
                      </div>

                      <div className="mt-4 flex items-center justify-end gap-3 border-t border-[#eef2f6] pt-3.5">
                        {item.status === "pending" || item.status === "processing" ? (
                          <>
                            <button
                              className="rounded-[12px] border border-[#ef4444]/30 px-4 py-2 text-[14px] font-semibold text-[#ef4444]"
                              onClick={() => void updateRefund(item.id, "reject")}
                              type="button"
                            >
                              拒绝
                            </button>
                            <button
                              className="rounded-[12px] bg-[#172033] px-4 py-2 text-[14px] font-semibold text-white"
                              onClick={() => void updateRefund(item.id, "approve")}
                              type="button"
                            >
                              {item.status === "processing" ? "查询并继续退款" : "通过并退款"}
                            </button>
                          </>
                        ) : (
                          <div className="text-[13px] text-[#98a2b3]">
                            {item.reviewed_at ? `处理时间：${new Date(item.reviewed_at).toLocaleString("zh-CN")}` : "已处理"}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {items.length === 0 ? (
                  <div className="rounded-[18px] border border-[#dbe3ef] bg-white px-6 py-10 text-center text-[15px] text-[#98a2b3]">
                    暂无退款申请
                  </div>
                ) : null}

                <div className="flex items-center justify-between pt-2">
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
              </div>
            </Panel>
          </div>
        </AdminShell>
      )}
    </AuthGuard>
  );
}
