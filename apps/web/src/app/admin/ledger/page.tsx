"use client";

import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminLedger, PaginatedResponse } from "@/types";

export default function AdminLedgerPage() {
  const [items, setItems] = useState<AdminLedger[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  useEffect(() => {
    let active = true;
    void apiFetch<PaginatedResponse<AdminLedger>>(`/admin/ledger?page=${page}&page_size=${pageSize}`).then((result) => {
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
          <Panel title="账务管理" subtitle="查看充值、消费与人工调账的完整账本流水。">
            <div className="overflow-hidden rounded-[28px] border border-[#dbe3ef]">
              <table className="w-full text-left">
                <thead className="bg-[#f8fafc] text-sm text-[#667085]">
                  <tr>
                    <th className="px-5 py-4">用户</th>
                    <th className="px-5 py-4">类型</th>
                    <th className="px-5 py-4">金额</th>
                    <th className="px-5 py-4">余额</th>
                    <th className="px-5 py-4">来源</th>
                    <th className="px-5 py-4">说明</th>
                    <th className="px-5 py-4">时间</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-[#eef2f6]">
                      <td className="px-5 py-4">
                        <div>{item.user_name}</div>
                        <div className="text-sm text-[#667085]">{item.user_email}</div>
                      </td>
                      <td className="px-5 py-4">{item.type}</td>
                      <td className="px-5 py-4">¥{item.amount}</td>
                      <td className="px-5 py-4">¥{item.balance_after}</td>
                      <td className="px-5 py-4">{item.reference_type}</td>
                      <td className="px-5 py-4">{item.description}</td>
                      <td className="px-5 py-4">{new Date(item.created_at).toLocaleString("zh-CN")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
