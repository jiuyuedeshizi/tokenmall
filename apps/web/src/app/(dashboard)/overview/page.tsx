"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { DashboardSummary } from "@/types";

function PulseIcon() {
  return (
    <svg aria-hidden="true" className="h-7 w-7" fill="none" viewBox="0 0 24 24">
      <path
        d="M3 12h4l2.2-5 4.2 11 2.2-6H21"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.2"
      />
    </svg>
  );
}

function WalletIcon() {
  return (
    <svg aria-hidden="true" className="h-7 w-7" fill="none" viewBox="0 0 24 24">
      <path
        d="M4 7a2 2 0 0 1 2-2h11v14H6a2 2 0 0 1-2-2V7Z"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path d="M17 9h3v6h-3" stroke="currentColor" strokeWidth="2" />
      <circle cx="17.5" cy="12" fill="currentColor" r="1" />
    </svg>
  );
}

function TrendIcon() {
  return (
    <svg aria-hidden="true" className="h-7 w-7" fill="none" viewBox="0 0 24 24">
      <path
        d="M4 16l5-5 4 4 7-7"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.2"
      />
      <path d="M15 8h5v5" stroke="currentColor" strokeWidth="2.2" />
    </svg>
  );
}

function RateIcon() {
  return (
    <svg aria-hidden="true" className="h-7 w-7" fill="none" viewBox="0 0 24 24">
      <path
        d="M4 16l5-5 4 4 7-7"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.2"
      />
      <path d="M15 8h5v5" stroke="currentColor" strokeWidth="2.2" />
    </svg>
  );
}

function ChartFrame({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[28px] border border-[var(--line)] bg-white p-8 shadow-[var(--card-shadow)]">
      <h3 className="text-[20px] font-semibold tracking-tight text-[#172033]">{title}</h3>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function OverviewMetric({
  icon,
  iconTone,
  title,
  value,
  hint,
}: {
  icon: React.ReactNode;
  iconTone: string;
  title: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-[24px] border border-[var(--line)] bg-white p-7 shadow-[var(--card-shadow)]">
      <div className="flex items-start justify-between gap-4">
        <div className={`flex h-14 w-14 items-center justify-center rounded-2xl ${iconTone}`}>
          {icon}
        </div>
        <div className="text-sm text-[var(--text-muted)]">{hint}</div>
      </div>
      <div className="mt-7 text-[20px] font-semibold text-[#172033]">{value}</div>
      <div className="mt-1.5 text-[15px] text-[var(--text-muted)]">{title}</div>
    </div>
  );
}

function BarChart({ data }: { data: { label: string; value: number }[] }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    value: Math.round(max * ratio),
    ratio,
  }));
  const xPositions = data.map((_, index) => {
    const count = Math.max(data.length - 1, 1);
    return `${(index * 100) / count}%`;
  });

  return (
    <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-4">
      <div className="relative h-[300px] text-right text-[13px] text-[#667085]">
        {ticks
          .slice()
          .reverse()
          .map((tick) => (
            <div
              key={tick.ratio}
              className="absolute right-0 flex -translate-y-1/2 items-center"
              style={{ top: `${100 - tick.ratio * 100}%` }}
            >
              {tick.value}
            </div>
          ))}
      </div>
      <div className="grid h-[300px] grid-rows-[minmax(0,1fr)_auto] gap-3">
        <div className="relative flex items-end gap-5 border-l border-b border-[#98a2b3] px-3">
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
            <div
              key={ratio}
              className="pointer-events-none absolute left-0 right-0 border-t border-dashed border-[#d0d5dd]"
              style={{ bottom: `${ratio * 100}%` }}
            />
          ))}
          {xPositions.map((left, index) => (
            <div
              key={`${data[index]?.label ?? index}-x-grid`}
              className="pointer-events-none absolute bottom-0 top-0 border-l border-dashed border-[#d0d5dd]"
              style={{ left }}
            />
          ))}
          {data.map((item) => (
            <div key={item.label} className="flex h-full flex-1 items-end justify-center">
              <div
                className="w-full rounded-t-[6px] bg-[#3f7ae8]"
                style={{ height: `${Math.max((item.value / max) * 100, 3)}%` }}
              />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-6 gap-5 px-3 text-center text-[14px] text-[#667085]">
          {data.map((item) => (
            <div key={item.label}>{item.label}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function LineChart({ data }: { data: { label: string; value: number }[] }) {
  const width = 560;
  const height = 240;
  const max = Math.max(...data.map((item) => item.value), 1);
  const min = 0;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    value: Math.round(max * ratio),
    ratio,
  }));

  const points = data.map((item, index) => {
    const x = (index * width) / Math.max(data.length - 1, 1);
    const y = height - ((item.value - min) / Math.max(max - min, 1)) * height;
    return { ...item, x, y };
  });

  const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-4">
      <div className="relative h-[300px] text-right text-[13px] text-[#667085]">
        {ticks
          .slice()
          .reverse()
          .map((tick) => (
            <div
              key={tick.ratio}
              className="absolute right-0 flex -translate-y-1/2 items-center"
              style={{ top: `${100 - tick.ratio * 100}%` }}
            >
              {tick.value}
            </div>
          ))}
      </div>
      <div className="grid h-[300px] grid-rows-[minmax(0,1fr)_auto] gap-3">
        <div className="relative border-l border-b border-[#98a2b3]">
          <svg className="h-full w-full" preserveAspectRatio="none" viewBox={`0 0 ${width} ${height}`}>
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
              const y = height - ratio * height;
              return (
                <line
                  key={ratio}
                  stroke="#d0d5dd"
                  strokeDasharray="4 4"
                  strokeWidth="1"
                  x1={0}
                  x2={width}
                  y1={y}
                  y2={y}
                />
              );
            })}
            {points.map((point) => (
              <line
                key={point.label}
                stroke="#d0d5dd"
                strokeDasharray="4 4"
                strokeWidth="1"
                x1={point.x}
                x2={point.x}
                y1={0}
                y2={height}
              />
            ))}
            <polyline
              fill="none"
              points={polyline}
              stroke="#12b981"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="3"
            />
            {points.map((point) => (
              <circle key={point.label} cx={point.x} cy={point.y} fill="#fff" r="4.5" stroke="#12b981" strokeWidth="2.5" />
            ))}
          </svg>
        </div>
        <div className="grid grid-cols-7 gap-2 px-1 text-center text-[14px] text-[#667085]">
          {data.map((item) => (
            <div key={item.label}>{item.label}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    void apiFetch<DashboardSummary>("/dashboard/summary").then(setSummary);
  }, []);

  const metrics = useMemo(
    () => [
      {
        title: "总请求数",
        value: (summary?.total_requests ?? 0).toLocaleString(),
        hint: "成功请求累计",
        icon: <PulseIcon />,
        iconTone: "bg-[#dbe8ff] text-[#315efb]",
      },
      {
        title: "本月消费",
        value: `¥${summary?.month_spend ?? "0.0000"}`,
        hint: "本月实际扣费",
        icon: <WalletIcon />,
        iconTone: "bg-[#dcfce7] text-[#16a34a]",
      },
      {
        title: "余额",
        value: `¥${summary?.token_balance ?? "0.0000"}`,
        hint: "当前钱包余额",
        icon: <TrendIcon />,
        iconTone: "bg-[#efe0ff] text-[#8b5cf6]",
      },
      {
        title: "成功率",
        value: `${summary?.success_rate ?? 0}%`,
        hint: "按调用日志统计",
        icon: <RateIcon />,
        iconTone: "bg-[#d9fbe8] text-[#12b981]",
      },
    ],
    [summary],
  );

  return (
    <div className="space-y-8">
      <Panel title="使用情况概览">
        <div className="space-y-8">
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((item) => (
              <OverviewMetric
                key={item.title}
                hint={item.hint}
                icon={item.icon}
                iconTone={item.iconTone}
                title={item.title}
                value={item.value}
              />
            ))}
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <ChartFrame title="月度使用情况">
              <BarChart data={summary?.monthly_usage ?? []} />
            </ChartFrame>
            <ChartFrame title="本周每日使用">
              <LineChart data={summary?.weekly_usage ?? []} />
            </ChartFrame>
          </div>

          <section className="rounded-[28px] border border-[var(--line)] bg-white p-8 shadow-[var(--card-shadow)]">
            <h3 className="text-[20px] font-semibold tracking-tight text-[#172033]">最近活动</h3>
            <div className="mt-6 divide-y divide-[var(--line)]">
              {(summary?.recent_activities ?? []).map((item, index) => (
                <div
                  key={`${item.time}-${item.title}-${index}`}
                  className="grid grid-cols-[72px_minmax(0,1fr)_auto] items-center gap-4 py-5"
                >
                  <div className="text-[15px] text-[#667085]">{item.time}</div>
                  <div className="flex min-w-0 items-center gap-3 text-[16px]">
                    <span className="truncate font-semibold text-[#172033]">{item.title}</span>
                    <span className="truncate text-[#667085]">({item.subtitle})</span>
                  </div>
                  <div className="flex items-center gap-7 whitespace-nowrap text-right">
                    <div className="text-[15px] text-[#667085]">
                      {item.tokens > 0 ? `${item.tokens} tokens` : ""}
                    </div>
                    <div className="text-[16px] font-semibold text-[#16a34a]">¥{item.amount}</div>
                  </div>
                </div>
              ))}
              {summary && summary.recent_activities.length === 0 ? (
                <div className="py-8 text-center text-[15px] text-[var(--text-muted)]">暂无活动记录</div>
              ) : null}
            </div>
          </section>
        </div>
      </Panel>
    </div>
  );
}
