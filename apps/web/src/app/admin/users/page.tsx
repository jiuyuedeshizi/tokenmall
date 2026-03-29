"use client";

import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminUser, PaginatedResponse } from "@/types";

function formatUserStatus(status: string) {
  return status === "active" ? "启用中" : status === "disabled" ? "已禁用" : status;
}

export default function AdminUsersPage() {
  const [items, setItems] = useState<AdminUser[]>([]);
  const [adjustingId, setAdjustingId] = useState<number | null>(null);
  const [resetPasswordUser, setResetPasswordUser] = useState<AdminUser | null>(null);
  const [adjustAmount, setAdjustAmount] = useState("100");
  const [adjustDescription, setAdjustDescription] = useState("管理员调整余额");
  const [newPassword, setNewPassword] = useState("");
  const [notice, setNotice] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  async function load() {
    const result = await apiFetch<PaginatedResponse<AdminUser>>(`/admin/users?page=${page}&page_size=${pageSize}`);
    setItems(result.items);
    setTotal(result.total);
  }

  useEffect(() => {
    let active = true;
    void apiFetch<PaginatedResponse<AdminUser>>(`/admin/users?page=${page}&page_size=${pageSize}`).then((result) => {
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
          <Panel title="用户管理" subtitle="查看用户状态、余额、Key 数量，并支持启停与调账。">
            <div className="overflow-hidden rounded-[28px] border border-[#dbe3ef]">
              <table className="w-full text-left">
                <thead className="bg-[#f8fafc] text-sm text-[#667085]">
                  <tr>
                    <th className="px-5 py-4">用户</th>
                    <th className="px-5 py-4">角色</th>
                    <th className="px-5 py-4">状态</th>
                    <th className="px-5 py-4">余额</th>
                    <th className="px-5 py-4">冻结</th>
                    <th className="px-5 py-4">Key</th>
                    <th className="px-5 py-4">注册时间</th>
                    <th className="px-5 py-4">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-[#eef2f6] align-top">
                      <td className="px-5 py-4">
                        <div className="font-medium">{item.name}</div>
                        <div className="text-sm text-[#667085]">{item.email}</div>
                      </td>
                      <td className="px-5 py-4">{item.role}</td>
                      <td className="px-5 py-4">{formatUserStatus(item.status)}</td>
                      <td className="px-5 py-4">¥{item.balance}</td>
                      <td className="px-5 py-4">¥{item.reserved_balance}</td>
                      <td className="px-5 py-4">{item.api_key_count}</td>
                      <td className="px-5 py-4">{new Date(item.created_at).toLocaleString()}</td>
                      <td className="px-5 py-4">
                        <div className="flex flex-wrap gap-2">
                          <button
                            className="rounded-full border border-[#dbe3ef] px-3 py-1 text-sm"
                            onClick={() =>
                              void apiFetch(`/admin/users/${item.id}/${item.status === "active" ? "disable" : "enable"}`, {
                                method: "POST",
                              })
                                .then(async () => {
                                  setNotice(item.status === "active" ? "用户已禁用" : "用户已启用");
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
                            className="rounded-full border border-[#315efb] px-3 py-1 text-sm text-[#315efb]"
                            onClick={() => setAdjustingId(adjustingId === item.id ? null : item.id)}
                            type="button"
                          >
                            调整余额
                          </button>
                          <button
                            className="rounded-full border border-[#172033] px-3 py-1 text-sm text-[#172033]"
                            onClick={() => {
                              setResetPasswordUser(item);
                              setNewPassword("");
                            }}
                            type="button"
                          >
                            重置密码
                          </button>
                        </div>
                        {adjustingId === item.id ? (
                          <div className="mt-3 space-y-2 rounded-[16px] bg-[#f8fafc] p-3">
                            <input
                              className="h-10 w-full rounded-xl border border-[#dbe3ef] px-3 text-sm outline-none"
                              onChange={(event) => setAdjustAmount(event.target.value)}
                              value={adjustAmount}
                            />
                            <input
                              className="h-10 w-full rounded-xl border border-[#dbe3ef] px-3 text-sm outline-none"
                              onChange={(event) => setAdjustDescription(event.target.value)}
                              value={adjustDescription}
                            />
                            <button
                              className="rounded-xl bg-[#315efb] px-3 py-2 text-sm font-semibold text-white"
                              onClick={() =>
                                void apiFetch(`/admin/users/${item.id}/adjust-balance`, {
                                  method: "POST",
                                  body: JSON.stringify({
                                    amount: Number(adjustAmount),
                                    description: adjustDescription,
                                  }),
                                })
                                  .then(async () => {
                                    setAdjustingId(null);
                                    setNotice("余额调整成功");
                                    await load();
                                  })
                                  .catch((error) => {
                                    setNotice(error instanceof Error ? error.message : "调整失败");
                                  })
                              }
                              type="button"
                            >
                              提交
                            </button>
                          </div>
                        ) : null}
                      </td>
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

          {resetPasswordUser ? (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#172033]/35 px-4">
              <div className="w-full max-w-[520px] rounded-[28px] bg-white shadow-[0_32px_80px_rgba(15,23,42,0.18)]">
                <div className="flex items-center justify-between border-b border-[#e5eaf3] px-8 py-6">
                  <div>
                    <h2 className="text-[24px] font-semibold text-[#172033]">重置用户密码</h2>
                    <p className="mt-2 text-[14px] text-[#667085]">
                      为 {resetPasswordUser.name} 设置新的登录密码。
                    </p>
                  </div>
                  <button
                    className="text-[30px] leading-none text-[#98a2b3]"
                    onClick={() => setResetPasswordUser(null)}
                    type="button"
                  >
                    ×
                  </button>
                </div>
                <div className="space-y-4 px-8 py-7">
                  <div className="rounded-[20px] bg-[#f8fafc] p-5">
                    <div className="text-[13px] text-[#98a2b3]">账号邮箱</div>
                    <div className="mt-1 text-[15px] font-semibold text-[#172033]">{resetPasswordUser.email}</div>
                  </div>
                  <label className="block">
                    <div className="mb-2 text-[14px] font-medium text-[#4d596a]">新密码</div>
                    <input
                      className="h-[50px] w-full rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                      onChange={(event) => setNewPassword(event.target.value)}
                      placeholder="请输入至少 8 位的新密码"
                      type="password"
                      value={newPassword}
                    />
                  </label>
                </div>
                <div className="flex justify-end gap-3 border-t border-[#e5eaf3] px-8 py-5">
                  <button
                    className="rounded-[14px] border border-[#dbe3ef] px-5 py-3 text-[15px] font-semibold text-[#4d596a]"
                    onClick={() => setResetPasswordUser(null)}
                    type="button"
                  >
                    取消
                  </button>
                    <button
                    className="rounded-[14px] bg-[#172033] px-6 py-3 text-[15px] font-semibold text-white disabled:opacity-60"
                    disabled={newPassword.trim().length < 8}
                    onClick={() =>
                      void apiFetch(`/admin/users/${resetPasswordUser.id}/reset-password`, {
                        method: "POST",
                        body: JSON.stringify({ new_password: newPassword }),
                      })
                        .then(async () => {
                          setResetPasswordUser(null);
                          setNotice("密码已重置");
                          await load();
                        })
                        .catch((error) => {
                          setNotice(error instanceof Error ? error.message : "重置失败");
                        })
                    }
                    type="button"
                  >
                    确认重置
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </AdminShell>
      )}
    </AuthGuard>
  );
}
