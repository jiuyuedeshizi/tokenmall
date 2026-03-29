"use client";

import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminOrder, PaginatedResponse } from "@/types";

function formatOrderStatus(status: string) {
  return status === "paid" ? "成功" : status === "pending" ? "待支付" : status;
}

export default function AdminOrdersPage() {
  const [items, setItems] = useState<AdminOrder[]>([]);
  const [notice, setNotice] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  async function load() {
    const result = await apiFetch<PaginatedResponse<AdminOrder>>(`/admin/orders?page=${page}&page_size=${pageSize}`);
    setItems(result.items);
    setTotal(result.total);
  }

  useEffect(() => {
    let active = true;
    void apiFetch<PaginatedResponse<AdminOrder>>(`/admin/orders?page=${page}&page_size=${pageSize}`).then((result) => {
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
          <Panel title="订单管理" subtitle="查看用户充值订单，并支持人工置为成功。">
            <div className="space-y-4">
              {items.map((item) => (
                <div key={item.order_no} className="flex items-center justify-between rounded-[24px] border border-[#dbe3ef] px-5 py-4">
                  <div>
                    <div className="font-medium">{item.order_no}</div>
                    <div className="mt-1 text-sm text-[#667085]">
                      {item.user_name} / {item.user_email}
                    </div>
                    <div className="mt-1 text-sm text-[#667085]">{item.payment_method}</div>
                  </div>
                  <div className="text-right">
                    <div>¥{item.amount}</div>
                    <div className="mt-1 text-sm text-[#667085]">{formatOrderStatus(item.status)}</div>
                    {item.status !== "paid" ? (
                      <button
                        className="mt-3 rounded-full bg-[#315efb] px-4 py-2 text-sm font-semibold text-white"
                        onClick={() =>
                          void apiFetch(`/admin/orders/${item.order_no}/mark-paid`, {
                            method: "POST",
                          })
                            .then(async () => {
                              await load();
                              setNotice("订单已标记为成功");
                            })
                            .catch((error) => {
                              setNotice(error instanceof Error ? error.message : "操作失败");
                            })
                        }
                        type="button"
                      >
                        标记成功
                      </button>
                    ) : null}
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
