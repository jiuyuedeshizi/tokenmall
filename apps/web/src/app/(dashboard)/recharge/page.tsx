"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { PaginatedResponse, PaymentOrder, Wallet } from "@/types";

const presets = [50, 100, 200, 500, 1000, 2000];

const paymentOptions = [
  {
    value: "alipay",
    label: "支付宝",
    iconUrl:
      "https://s3plus.meituan.net/nocode-external/nocode_image/default/image-3w7oz4o5wg924sbmedsbja85y5yj2r.png",
  },
  {
    value: "wechat",
    label: "微信支付",
    iconUrl:
      "https://s3plus.meituan.net/nocode-external/nocode_image/default/333c4c1c-7bf4-4af3-a8ac-aadf1c4911bb-uwc55mpvgst2u8riaymnfqcz6q6yjk.png",
  },
  {
    value: "unionpay",
    label: "银行卡支付",
    iconUrl:
      "https://s3plus.meituan.net/nocode-external/nocode_image/default/image-91vzgr1eal3m5so4p6hq5u6o14nzhs.png",
  },
];

function formatAmount(value: string | number) {
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return "0";
  }
  return amount.toLocaleString("zh-CN", {
    minimumFractionDigits: amount % 1 === 0 ? 0 : 4,
    maximumFractionDigits: 4,
  });
}

function formatStatus(status: string) {
  if (status === "paid") {
    return "成功";
  }
  if (status === "pending") {
    return "待支付";
  }
  return status;
}

export default function RechargePage() {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [orders, setOrders] = useState<PaymentOrder[]>([]);
  const [amount, setAmount] = useState("100");
  const [paymentMethod, setPaymentMethod] = useState("alipay");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [activeOrder, setActiveOrder] = useState<PaymentOrder | null>(null);
  const [checkingPayment, setCheckingPayment] = useState(false);

  const loadData = useCallback(async () => {
    const [walletData, orderData] = await Promise.all([
      apiFetch<Wallet>("/wallet"),
      apiFetch<PaginatedResponse<PaymentOrder>>("/payments/orders?page=1&page_size=10"),
    ]);
    setWallet(walletData);
    setOrders(orderData.items);
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!notice) {
      return;
    }
    const timer = window.setTimeout(() => setNotice(""), 2200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  async function handleRecharge() {
    setSubmitting(true);
    try {
      const order = await apiFetch<PaymentOrder>("/payments/orders", {
        method: "POST",
        body: JSON.stringify({ amount: Number(amount), payment_method: paymentMethod }),
      });
      setActiveOrder(order);
      setNotice("支付订单已创建，请完成支付");
      await loadData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "创建支付订单失败");
    } finally {
      setSubmitting(false);
    }
  }

  const refreshActiveOrder = useCallback(async () => {
    if (!activeOrder) {
      return;
    }
    setCheckingPayment(true);
    try {
      const latest = await apiFetch<PaymentOrder>(`/payments/orders/${activeOrder.order_no}`);
      setActiveOrder(latest);
      await loadData();
      if (latest.status === "paid") {
        setNotice("支付成功，余额已到账");
        window.setTimeout(() => {
          setActiveOrder(null);
        }, 1200);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "刷新支付状态失败");
    } finally {
      setCheckingPayment(false);
    }
  }, [activeOrder, loadData]);

  useEffect(() => {
    if (!activeOrder || activeOrder.status === "paid") {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshActiveOrder();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [activeOrder, refreshActiveOrder]);

  const selectedAmount = useMemo(() => formatAmount(amount), [amount]);

  return (
    <Panel title="充值中心">
      {notice ? (
        <div className="mb-5 rounded-[18px] bg-[#172033] px-4 py-3 text-[14px] text-white">
          {notice}
        </div>
      ) : null}
      <div className="grid gap-8 xl:grid-cols-[1.7fr_0.83fr]">
        <section className="space-y-8">
          <div>
            <div className="text-[16px] font-semibold text-[#172033]">选择充值金额</div>
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              {presets.map((preset) => {
                const selected = amount === String(preset);
                return (
                  <button
                    key={preset}
                    className={`rounded-[18px] border px-6 py-7 text-[22px] font-semibold transition ${
                      selected
                        ? "border-[#3a74f7] bg-[#eef4ff] text-[#315efb]"
                        : "border-[#d8e0eb] bg-white text-[#172033]"
                    }`}
                    onClick={() => setAmount(String(preset))}
                    type="button"
                  >
                    ¥{preset}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div className="text-[16px] font-semibold text-[#172033]">自定义金额</div>
            <div className="mt-4">
              <div className="flex h-[62px] items-center rounded-[18px] border border-[#d8e0eb] bg-white px-5">
                <span className="mr-3 text-[24px] text-[#a0a9b8]">¥</span>
                <input
                  className="w-full border-0 bg-transparent text-[18px] text-[#172033] outline-none placeholder:text-[#a0a9b8]"
                  inputMode="decimal"
                  placeholder="100"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                />
              </div>
            </div>
          </div>

          <div>
            <div className="text-[16px] font-semibold text-[#172033]">支付方式</div>
            <div className="mt-4 space-y-4">
              {paymentOptions.map((option) => {
                const selected = paymentMethod === option.value;
                return (
                  <button
                    key={option.value}
                    className={`flex w-full items-center justify-between rounded-[18px] border px-5 py-5 text-left transition ${
                      selected
                        ? "border-[#3a74f7] bg-[#f9fbff]"
                        : "border-[#d8e0eb] bg-white"
                    }`}
                    onClick={() => setPaymentMethod(option.value)}
                    type="button"
                  >
                    <div className="flex items-center gap-4">
                      <span
                        className={`flex h-6 w-6 items-center justify-center rounded-full border-2 ${
                          selected ? "border-[#1677ff]" : "border-[#97a0af]"
                        }`}
                      >
                      <span
                        className={`h-3.5 w-3.5 rounded-full ${
                            selected ? "bg-[#1677ff]" : "bg-transparent"
                        }`}
                      />
                    </span>
                      <span className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-lg bg-white">
                        <Image
                          alt={option.label}
                          className="h-8 w-8 object-contain"
                          src={option.iconUrl}
                          height={32}
                          unoptimized
                          width={32}
                        />
                      </span>
                      <span className="text-[16px] font-semibold text-[#172033]">{option.label}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <button
            className="mt-2 flex h-[62px] w-full items-center justify-center rounded-[18px] bg-[#315efb] text-[20px] font-semibold text-white transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={submitting || !Number(amount)}
            onClick={() => void handleRecharge()}
            type="button"
          >
            {submitting ? "充值处理中..." : `立即充值 ¥${selectedAmount}`}
          </button>
        </section>

        <section className="space-y-6">
          <div className="rounded-[24px] bg-[#eef4ff] p-8">
            <div className="text-[16px] font-semibold text-[#172033]">当前余额</div>
            <div className="mt-7 text-[52px] font-semibold leading-none tracking-tight text-[#315efb]">
              {formatAmount(wallet?.balance ?? 0)}
            </div>
            <button
              className="mt-8 flex h-[54px] w-full items-center justify-center rounded-[16px] bg-[#315efb] text-[18px] font-semibold text-white"
              onClick={() => setAmount("100")}
              type="button"
            >
              购买更多
            </button>
          </div>

          <div className="rounded-[24px] bg-[#f8fafc] p-8">
            <div className="flex items-center justify-between">
              <div className="text-[16px] font-semibold text-[#172033]">最近交易</div>
              <div className="text-[14px] text-[#98a2b3]">最近 3 条</div>
            </div>
            <div className="mt-6 space-y-5">
              {orders.slice(0, 3).map((order) => (
                <div key={order.order_no} className="border-b border-[#e5e7eb] pb-4 last:border-b-0 last:pb-0">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-[18px] font-semibold text-[#172033]">¥{formatAmount(order.amount)}</div>
                      <div className="mt-1 text-[14px] text-[#667085]">
                        {new Date(order.created_at).toLocaleDateString("zh-CN")}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[18px] font-semibold text-[#172033]">
                        +{Math.round(Number(order.amount) * 100).toLocaleString()}
                      </div>
                      <div
                        className={`mt-1 text-[14px] font-semibold ${
                          order.status === "paid" ? "text-[#16a34a]" : "text-[#667085]"
                        }`}
                      >
                        {formatStatus(order.status)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {orders.length === 0 ? (
                <div className="text-[14px] text-[#98a2b3]">暂无充值记录</div>
              ) : null}
            </div>
          </div>
        </section>
      </div>

      {activeOrder ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#172033]/35 px-4">
          <div className="w-full max-w-[520px] rounded-[28px] bg-white p-8 shadow-[0_32px_80px_rgba(15,23,42,0.18)]">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-[28px] font-semibold text-[#172033]">完成支付</h2>
                <p className="mt-2 text-[15px] text-[#667085]">
                  订单号 {activeOrder.order_no}
                </p>
              </div>
              <button
                className="text-[30px] leading-none text-[#98a2b3]"
                onClick={() => setActiveOrder(null)}
                type="button"
              >
                ×
              </button>
            </div>

            <div className="mt-6 rounded-[24px] bg-[#f8fafc] p-6 text-center">
              <div className="text-[16px] font-semibold text-[#172033]">
                应付金额 ¥{formatAmount(activeOrder.amount)}
              </div>
              <div className="mt-2 text-[14px] text-[#667085]">
                已自动轮询支付状态，完成支付后会自动到账并关闭弹窗
              </div>
              {activeOrder.qr_code_image ? (
                <Image
                  alt="支付二维码"
                  className="mx-auto mt-5 h-[220px] w-[220px] rounded-[20px] border border-[#dbe3ef] bg-white p-3"
                  src={activeOrder.qr_code_image}
                  height={220}
                  unoptimized
                  width={220}
                />
              ) : null}
              {activeOrder.payment_url ? (
                <a
                  className="mt-5 inline-flex rounded-[14px] bg-[#315efb] px-5 py-3 text-[15px] font-semibold text-white"
                  href={activeOrder.payment_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  {activeOrder.payment_method === "unionpay" ? "打开银联收银台" : "打开支付链接"}
                </a>
              ) : null}
              {!activeOrder.qr_code_image && !activeOrder.payment_url ? (
                <div className="mt-5 text-[14px] text-[#667085]">
                  当前支付渠道未返回二维码或支付链接，请检查支付配置。
                </div>
              ) : null}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                className="rounded-[14px] border border-[#dbe3ef] px-5 py-3 text-[15px] font-semibold text-[#4d596a]"
                onClick={() => setActiveOrder(null)}
                type="button"
              >
                关闭
              </button>
              <div className="flex items-center rounded-[14px] bg-[#172033] px-5 py-3 text-[15px] font-semibold text-white">
                {checkingPayment ? "正在检查支付状态..." : "等待支付完成"}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </Panel>
  );
}
