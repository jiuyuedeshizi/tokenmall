"use client";

import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminOverview } from "@/types";

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-[24px] border border-[#dbe3ef] bg-white p-6">
      <div className="text-[14px] text-[#667085]">{label}</div>
      <div className="mt-4 text-[32px] font-semibold text-[#172033]">{value}</div>
    </div>
  );
}

export default function AdminOverviewPage() {
  const [summary, setSummary] = useState<AdminOverview | null>(null);

  useEffect(() => {
    void apiFetch<AdminOverview>("/admin/overview").then(setSummary);
  }, []);

  return (
    <AuthGuard>
      {({ user }) => (
        <AdminShell user={user}>
          <div className="space-y-8">
            <Panel title="平台概览" subtitle="统一查看平台运营、账务与异常情况。">
              <div className="grid gap-5 xl:grid-cols-4">
                <MetricCard label="总用户数" value={summary?.total_users ?? 0} />
                <MetricCard label="活跃用户" value={summary?.active_users ?? 0} />
                <MetricCard label="总请求数" value={summary?.total_requests ?? 0} />
                <MetricCard label="本月消费" value={`¥${summary?.month_spend ?? "0.0000"}`} />
                <MetricCard label="API Key 数量" value={summary?.total_api_keys ?? 0} />
                <MetricCard label="启用模型数" value={summary?.active_models ?? 0} />
                <MetricCard label="成功率" value={`${summary?.success_rate ?? 100}%`} />
                <MetricCard label="待处理订单" value={summary?.pending_orders ?? 0} />
              </div>
            </Panel>

            <div className="grid gap-8 xl:grid-cols-2">
              <Panel title="最近订单">
                <div className="space-y-4">
                  {summary?.recent_orders.map((item) => (
                    <div
                      key={item.order_no}
                      className="flex items-center justify-between rounded-[20px] border border-[#e5eaf3] px-5 py-4"
                    >
                      <div>
                        <div className="font-semibold text-[#172033]">{item.order_no}</div>
                        <div className="mt-1 text-[14px] text-[#667085]">
                          {new Date(item.created_at).toLocaleString("zh-CN")}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-[#172033]">¥{item.amount}</div>
                        <div className="mt-1 text-[14px] text-[#667085]">{item.status}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </Panel>

              <Panel title="最近异常">
                <div className="space-y-4">
                  {summary?.recent_errors.map((item) => (
                    <div
                      key={`${item.request_id}-${item.created_at}`}
                      className="rounded-[20px] border border-[#f1d3d3] bg-[#fff7f7] px-5 py-4"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="font-semibold text-[#172033]">{item.model_code}</div>
                        <div className="text-[14px] text-[#667085]">
                          {new Date(item.created_at).toLocaleString("zh-CN")}
                        </div>
                      </div>
                      <div className="mt-3 text-[14px] text-[#b42318]">{item.error_message || "未知错误"}</div>
                    </div>
                  ))}
                </div>
              </Panel>
            </div>
          </div>
        </AdminShell>
      )}
    </AuthGuard>
  );
}
