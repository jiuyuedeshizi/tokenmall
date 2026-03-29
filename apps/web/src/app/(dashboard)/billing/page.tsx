"use client";

import { useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { PaginatedResponse, PaymentOrder, RefundRequest, RefundSummary } from "@/types";

function formatStatus(status: string) {
  return status === "paid" ? "成功" : status === "pending" ? "待支付" : status;
}

function formatRefundStatus(status: string) {
  if (status === "refunded" || status === "approved") {
    return { label: "已退款", color: "text-[#22c55e]", icon: "check" };
  }
  if (status === "rejected") {
    return { label: "已拒绝", color: "text-[#ef4444]", icon: "close" };
  }
  if (status === "processing") {
    return { label: "部分退款", color: "text-[#f59e0b]", icon: "clock" };
  }
  return { label: "处理中", color: "text-[#eab308]", icon: "clock" };
}

export default function BillingPage() {
  const [items, setItems] = useState<PaymentOrder[]>([]);
  const [activeTab, setActiveTab] = useState("recharge");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [notice, setNotice] = useState("");
  const [refundOpen, setRefundOpen] = useState(false);
  const [refundTab, setRefundTab] = useState<"apply" | "history">("apply");
  const [refundSummary, setRefundSummary] = useState<RefundSummary | null>(null);
  const [refundHistory, setRefundHistory] = useState<RefundRequest[]>([]);
  const [refundReason, setRefundReason] = useState("");
  const [refundSubmitting, setRefundSubmitting] = useState(false);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  useEffect(() => {
    if (activeTab !== "recharge") {
      return;
    }
    void apiFetch<PaginatedResponse<PaymentOrder>>(`/payments/orders?page=${page}&page_size=${pageSize}`).then((result) => {
      setItems(result.items);
      setTotal(result.total);
    });
  }, [activeTab, page]);

  useEffect(() => {
    if (!notice) {
      return;
    }
    const timer = window.setTimeout(() => setNotice(""), 2200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  async function loadRefundData() {
    const [summary, history] = await Promise.all([
      apiFetch<RefundSummary>("/payments/refund-summary"),
      apiFetch<PaginatedResponse<RefundRequest>>("/payments/refunds?page=1&page_size=20"),
    ]);
    setRefundSummary(summary);
    setRefundHistory(history.items);
  }

  async function openRefundModal() {
    setRefundOpen(true);
    setRefundTab("apply");
    await loadRefundData();
  }

  async function submitRefund() {
    setRefundSubmitting(true);
    try {
      await apiFetch<RefundRequest>("/payments/refunds", {
        method: "POST",
        body: JSON.stringify({ reason: refundReason }),
      });
      setNotice("退款申请已提交");
      setRefundReason("");
      setRefundTab("history");
      await loadRefundData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "退款申请提交失败");
    } finally {
      setRefundSubmitting(false);
    }
  }

  const visibleItems = useMemo(
    () => (activeTab === "recharge" ? items : []),
    [activeTab, items],
  );
  const visibleTotal = activeTab === "recharge" ? total : 0;
  const visibleTotalPages = activeTab === "recharge" ? totalPages : 1;

  return (
    <Panel title="账单">
      {notice ? (
        <div className="mb-5 rounded-[18px] bg-[#172033] px-4 py-3 text-[14px] text-white">{notice}</div>
      ) : null}
      <div className="space-y-7">
        <div className="flex items-center justify-between">
          <div className="flex gap-3">
            <button
              className={`rounded-[14px] px-5 py-3 text-[16px] font-semibold ${
                activeTab === "recharge"
                  ? "bg-[#f3f5f9] text-[#172033]"
                  : "text-[#98a2b3]"
              }`}
              onClick={() => {
                setActiveTab("recharge");
                setPage(1);
              }}
              type="button"
            >
              充值账单
            </button>
            <button
              className={`rounded-[14px] px-5 py-3 text-[16px] font-semibold ${
                activeTab === "gift" ? "bg-[#f3f5f9] text-[#172033]" : "text-[#98a2b3]"
              }`}
              onClick={() => {
                setActiveTab("gift");
                setPage(1);
              }}
              type="button"
            >
              赠送账单
            </button>
          </div>
          <div className="flex gap-8 text-[16px] font-semibold text-[#667085]">
            <button onClick={() => void openRefundModal()} type="button">退款管理</button>
            <button onClick={() => setNotice("发票管理敬请期待")} type="button">发票管理</button>
          </div>
        </div>

        <div className="overflow-hidden rounded-[24px] border border-[#e5e7eb] bg-white">
          <div className="grid grid-cols-[minmax(0,1.8fr)_160px_140px_240px] bg-[#f8fafc] px-8 py-5 text-[15px] font-semibold text-[#667085]">
            <div>订单编号</div>
            <div>状态</div>
            <div>金额</div>
            <div>创建时间</div>
          </div>

          {visibleItems.map((item) => (
            <div
              key={item.order_no}
              className="grid grid-cols-[minmax(0,1.8fr)_160px_140px_240px] items-center border-t border-[#eef2f6] px-8 py-6"
            >
              <div className="truncate text-[16px] text-[#172033]">{item.order_no}</div>
              <div className="text-[16px] font-semibold text-[#16a34a]">{formatStatus(item.status)}</div>
              <div className="text-[16px] text-[#172033]">¥{item.amount}</div>
              <div className="text-[16px] text-[#4d596a]">
                {new Date(item.created_at).toLocaleString("zh-CN")}
              </div>
            </div>
          ))}

          {visibleItems.length === 0 ? (
            <div className="px-8 py-10 text-[15px] text-[#98a2b3]">
              {activeTab === "gift" ? "暂无赠送账单" : "暂无充值账单"}
            </div>
          ) : null}
        </div>

        {activeTab === "recharge" ? (
          <div className="flex items-center justify-between">
            <div className="text-[14px] text-[#667085]">
              共 {visibleTotal} 条，当前第 {page} / {visibleTotalPages} 页
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
                disabled={page >= visibleTotalPages}
                onClick={() => setPage((prev) => Math.min(visibleTotalPages, prev + 1))}
                type="button"
              >
                下一页
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {refundOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#172033]/35 px-4 py-8">
          <div className="relative max-h-[88vh] w-full max-w-[840px] overflow-hidden rounded-[24px] bg-white shadow-[0_24px_80px_rgba(15,23,42,0.16)]">
            <div className="grid grid-cols-2 border-b border-[#d8e0eb]">
              {[
                { key: "apply", label: "申请退款" },
                { key: "history", label: "历史退款申请" },
              ].map((tab) => {
                const active = refundTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    className={`relative py-5 text-[18px] font-semibold ${
                      active ? "text-[#172033]" : "text-[#7c8798]"
                    }`}
                    onClick={() => setRefundTab(tab.key as "apply" | "history")}
                    type="button"
                  >
                    {tab.label}
                    <span
                      className={`absolute inset-x-0 bottom-0 h-[3px] ${active ? "bg-[#172033]" : "bg-transparent"}`}
                    />
                  </button>
                );
              })}
            </div>

            <div className="max-h-[calc(88vh-76px)] overflow-y-auto p-7">
              {refundTab === "apply" ? (
                <div className="space-y-7">
                  <div>
                    <h3 className="text-[18px] font-semibold text-[#172033]">提示</h3>
                    <div className="mt-4 space-y-3 text-[14px] leading-[1.8] text-[#4d596a]">
                      <p>1. 未消耗且未开具发票的充值余额，支持全额退款（人民币最小退款金额0.01元）</p>
                      <p>2. 已消耗金额不支持退款；已开票未消耗金额，前往发票管理页作废发票后再申请退款</p>
                      <p>3. 对公汇款暂不支持在线申请退款，如有需要请联系我们</p>
                      <p>4. 微信、支付宝超过12个月的订单不支持退款；Paypal 超过180天的订单不支持在线申请退款</p>
                      <p>5. 计费可能存在延迟，可退款金额为预估金额，实际退款金额以到账金额为准</p>
                      <p>6. 如退款申请通过，一般会在5个工作日内原路退回</p>
                      <p>7. 一个账号仅可存在一笔处理中退款申请</p>
                    </div>
                  </div>

                  <div>
                    <div className="text-[16px] font-medium text-[#4d596a]">
                      申请退款金额（线上充值金额 - 已开票/开票中金额 - 已消耗金额）
                    </div>
                    <div className="mt-3 text-[36px] font-semibold leading-none text-[#172033]">
                      ¥{refundSummary?.refundable_amount ?? "0.00"}
                    </div>
                  </div>

                  <div>
                    <label className="block text-[16px] font-semibold text-[#172033]">退款理由（选填）</label>
                    <textarea
                      className="mt-3 h-[132px] w-full rounded-[16px] border border-[#d8e0eb] px-4 py-3 text-[16px] text-[#172033] outline-none placeholder:text-[#a0a9b8]"
                      placeholder="请输入退款理由"
                      value={refundReason}
                      onChange={(event) => setRefundReason(event.target.value)}
                    />
                  </div>

                  <button
                    className="flex h-[58px] w-full items-center justify-center rounded-[16px] bg-[#172033] text-[20px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={refundSubmitting || !refundSummary || Number(refundSummary.refundable_amount) <= 0 || refundSummary.pending_exists}
                    onClick={() => void submitRefund()}
                    type="button"
                  >
                    {refundSubmitting
                      ? "提交中..."
                      : refundSummary?.pending_exists
                        ? "当前已有处理中退款申请"
                        : "提交"}
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {refundHistory.map((item) => {
                    const status = formatRefundStatus(item.status);
                    return (
                      <div key={item.request_no} className="rounded-[18px] border border-[#d8e0eb] bg-white p-6">
                        <div className="flex items-start justify-between gap-8">
                          <div className="flex-1">
                            <div className={`flex items-center gap-3 text-[18px] font-semibold ${status.color}`}>
                              <span className="flex h-8 w-8 items-center justify-center rounded-full border-[2px] border-current">
                                {status.icon === "check" ? (
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" viewBox="0 0 24 24">
                                    <path d="M6 12.5 10 16.5 18 7.5" />
                                  </svg>
                                ) : null}
                                {status.icon === "close" ? (
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="2.5" viewBox="0 0 24 24">
                                    <path d="M8 8l8 8M16 8l-8 8" />
                                  </svg>
                                ) : null}
                                {status.icon === "clock" ? (
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="2.2" viewBox="0 0 24 24">
                                    <circle cx="12" cy="12" r="8" />
                                    <path d="M12 7.5v5l3 2" />
                                  </svg>
                                ) : null}
                              </span>
                              <span>{status.label}</span>
                            </div>
                          <div className="mt-4 space-y-1.5 text-[15px] text-[#4d596a]">
                              <div>申请时间: {new Date(item.created_at).toLocaleString("zh-CN")}</div>
                              <div>
                                {item.refunded_at ? `退款时间: ${new Date(item.refunded_at).toLocaleString("zh-CN")}` : "退款时间: -"}
                              </div>
                              <div>已退金额: ¥{item.refunded_amount ?? "0.00"}</div>
                              <div>剩余金额: ¥{item.remaining_amount ?? item.amount}</div>
                            </div>
                          </div>
                          <div className="min-w-[220px] text-right">
                            <div className="text-[24px] font-semibold text-[#172033]">¥{item.amount}</div>
                            <div className="mt-3 text-[15px] text-[#667085]">订单号: {item.request_no}</div>
                          </div>
                        </div>
                        <div className="mt-6 border-t border-[#eef2f6] pt-4 text-[15px] text-[#4d596a]">
                          <div>退款理由: {item.reason || "申请退款"}</div>
                          {item.admin_note ? <div className="mt-2">处理说明: {item.admin_note}</div> : null}
                        </div>
                      </div>
                    );
                  })}

                  {refundHistory.length === 0 ? (
                    <div className="rounded-[18px] border border-[#d8e0eb] bg-white px-8 py-10 text-center text-[16px] text-[#98a2b3]">
                      暂无退款申请记录
                    </div>
                  ) : null}
                </div>
              )}
            </div>

            <button
              className="absolute right-5 top-4 text-[28px] leading-none text-[#98a2b3]"
              onClick={() => setRefundOpen(false)}
              type="button"
            >
              ×
            </button>
          </div>
        </div>
      ) : null}
    </Panel>
  );
}
