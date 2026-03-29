"use client";

import { useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { UsageHistoryResponse, UsageLog } from "@/types";

const timeOptions = [
  { label: "最近 7 天", value: 7 },
  { label: "最近 30 天", value: 30 },
  { label: "最近 90 天", value: 90 },
  { label: "自定义时间", value: "custom" },
];

const eventOptions = [
  { label: "全部事件", value: "all" },
  { label: "API 请求", value: "api" },
  { label: "Web Chat", value: "webchat" },
  { label: "Token 充值", value: "token_recharge" },
];

const weekLabels = ["日", "一", "二", "三", "四", "五", "六"];

function formatBadge(item: UsageLog) {
  return item.badge ?? (item.event_type === "token_recharge" ? "Token 充值" : "API");
}

function formatRowDate(value: string) {
  return new Date(value).toLocaleDateString("zh-CN", {
    month: "numeric",
    day: "numeric",
  }).replace("/", "月") + "日";
}

function formatCalendarButtonLabel(value: string) {
  if (!value) {
    return "年 / 月 / 日";
  }
  const [year, month, day] = value.split("-");
  return `${year}/${month}/${day}`;
}

function getTodayString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function monthKeyFromDate(value?: string) {
  if (value) {
    return value.slice(0, 7);
  }
  return getTodayString().slice(0, 7);
}

function formatCalendarHeader(monthKey: string) {
  const [year, month] = monthKey.split("-");
  return `${year}年${month}月`;
}

function shiftMonth(monthKey: string, offset: number) {
  const [year, month] = monthKey.split("-").map(Number);
  const next = new Date(year, month - 1 + offset, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}

function getCalendarDays(monthKey: string) {
  const [year, month] = monthKey.split("-").map(Number);
  const firstDay = new Date(year, month - 1, 1);
  const startWeekday = firstDay.getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const prevMonthDays = new Date(year, month - 1, 0).getDate();
  const cells: { key: string; value: string; day: number; currentMonth: boolean }[] = [];

  for (let index = 0; index < 42; index += 1) {
    const dayOffset = index - startWeekday + 1;
    if (dayOffset <= 0) {
      const date = new Date(year, month - 2, prevMonthDays + dayOffset);
      cells.push({
        key: `${date.toISOString()}-prev`,
        value: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`,
        day: date.getDate(),
        currentMonth: false,
      });
      continue;
    }
    if (dayOffset > daysInMonth) {
      const date = new Date(year, month - 1, dayOffset);
      cells.push({
        key: `${date.toISOString()}-next`,
        value: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`,
        day: date.getDate(),
        currentMonth: false,
      });
      continue;
    }
    cells.push({
      key: `${monthKey}-${dayOffset}`,
      value: `${year}-${String(month).padStart(2, "0")}-${String(dayOffset).padStart(2, "0")}`,
      day: dayOffset,
      currentMonth: true,
    });
  }

  return cells;
}

function buildQuery(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  return search.toString();
}

export default function UsagePage() {
  const [items, setItems] = useState<UsageLog[]>([]);
  const [keyword, setKeyword] = useState("");
  const [eventType, setEventType] = useState("all");
  const [timeFilter, setTimeFilter] = useState<number | "custom">(7);
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [isTimeOpen, setIsTimeOpen] = useState(false);
  const [isEventOpen, setIsEventOpen] = useState(false);
  const [calendarTarget, setCalendarTarget] = useState<"start" | "end" | null>(null);
  const [calendarMonth, setCalendarMonth] = useState(monthKeyFromDate());
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const pageSize = 10;

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const calendarDays = useMemo(() => getCalendarDays(calendarMonth), [calendarMonth]);

  useEffect(() => {
    let active = true;

    async function fetchUsageHistory() {
      setLoading(true);
      const query = buildQuery({
        keyword: keyword.trim() || undefined,
        event_type: eventType,
        range_days: timeFilter === "custom" ? undefined : timeFilter,
        start_date: timeFilter === "custom" ? customStart || undefined : undefined,
        end_date: timeFilter === "custom" ? customEnd || undefined : undefined,
        page,
        page_size: pageSize,
      });

      try {
        const result = await apiFetch<UsageHistoryResponse>(`/usage/logs?${query}`);
        if (!active) {
          return;
        }
        setItems(result.items);
        setTotal(result.total);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void fetchUsageHistory();

    return () => {
      active = false;
    };
  }, [keyword, eventType, timeFilter, customStart, customEnd, page]);

  const currentMonthLabel = useMemo(() => {
    return new Date().getFullYear() + "年" + (new Date().getMonth() + 1) + "月";
  }, []);

  function resetFilters() {
    setKeyword("");
    setEventType("all");
    setTimeFilter(7);
    setCustomStart("");
    setCustomEnd("");
    setPage(1);
    setIsTimeOpen(false);
    setIsEventOpen(false);
    setCalendarTarget(null);
  }

  return (
    <div className="space-y-6">
      <Panel title="使用历史">
        <div className="text-[17px] leading-7 text-[#667085]">
          按时间、来源和事件类型查看 API 活动。
        </div>
      </Panel>

      <Panel title="筛选条件">
        <div className="flex flex-col gap-4 xl:flex-row">
          <div className="flex-1">
            <div className="flex h-[54px] items-center rounded-[16px] border border-[#d8e0eb] bg-white px-4">
              <svg aria-hidden="true" className="h-5 w-5 text-[#98a2b3]" fill="none" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                <path d="m20 20-3.5-3.5" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
              </svg>
              <input
                className="ml-3 w-full border-0 bg-transparent text-[15px] text-[#172033] outline-none placeholder:text-[#98a2b3]"
                placeholder="搜索项目"
                value={keyword}
                onChange={(event) => {
                  setKeyword(event.target.value);
                  setPage(1);
                }}
              />
            </div>
          </div>
          <div className="relative">
            <button
              className="flex h-[54px] min-w-[144px] items-center justify-center rounded-[16px] border border-[#d8e0eb] bg-white px-5 text-[15px] font-semibold text-[#172033]"
              onClick={() => {
                setIsTimeOpen((prev) => !prev);
                setIsEventOpen(false);
              }}
              type="button"
            >
              {timeFilter === "custom"
                ? "自定义时间"
                : `最近 ${timeFilter} 天`}
            </button>
            {isTimeOpen ? (
              <div className="absolute right-0 top-[64px] z-20 w-[190px] rounded-[20px] border border-[#d8e0eb] bg-white p-3 shadow-[0_18px_45px_rgba(15,23,42,0.12)]">
                <div className="space-y-1">
                  {timeOptions.map((option) => {
                    const active = timeFilter === option.value;
                    return (
                      <button
                        key={String(option.value)}
                        className={`flex w-full items-center rounded-[14px] px-4 py-2.5 text-left text-[15px] font-semibold ${
                          active ? "bg-[#4a95ff] text-white" : "text-[#172033]"
                        }`}
                        onClick={() => {
                          setTimeFilter(option.value as number | "custom");
                          setPage(1);
                          setIsTimeOpen(false);
                        }}
                        type="button"
                      >
                        <span className="mr-2 inline-block w-4">{active ? "✓" : ""}</span>
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>

          <div className="relative">
            <button
              className="flex h-[54px] min-w-[144px] items-center justify-center rounded-[16px] border border-[#d8e0eb] bg-white px-5 text-[15px] font-semibold text-[#172033]"
              onClick={() => {
                setIsEventOpen((prev) => !prev);
                setIsTimeOpen(false);
              }}
              type="button"
            >
              {eventOptions.find((option) => option.value === eventType)?.label ?? "全部事件"}
            </button>
            {isEventOpen ? (
              <div className="absolute right-0 top-[64px] z-20 w-[190px] rounded-[20px] border border-[#d8e0eb] bg-white p-3 shadow-[0_18px_45px_rgba(15,23,42,0.12)]">
                <div className="space-y-1">
                  {eventOptions.map((option) => {
                    const active = eventType === option.value;
                    return (
                      <button
                        key={option.value}
                        className={`flex w-full items-center rounded-[14px] px-4 py-2.5 text-left text-[15px] font-semibold ${
                          active ? "bg-[#4a95ff] text-white" : "text-[#172033]"
                        }`}
                        onClick={() => {
                          setEventType(option.value);
                          setPage(1);
                          setIsEventOpen(false);
                        }}
                        type="button"
                      >
                        <span className="mr-2 inline-block w-4">{active ? "✓" : ""}</span>
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>

          <button
            className="flex h-[54px] w-[54px] items-center justify-center rounded-[16px] border border-[#d8e0eb] bg-white text-[#667085]"
            onClick={resetFilters}
            type="button"
          >
            <svg aria-hidden="true" className="h-7 w-7" fill="none" viewBox="0 0 24 24">
              <path
                d="M20 11a8 8 0 0 0-14.9-4M4 5v4h4M4 13a8 8 0 0 0 14.9 4M20 19v-4h-4"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
              />
            </svg>
          </button>
        </div>

        {timeFilter === "custom" ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="flex h-[78px] items-center justify-between rounded-[18px] border border-[#d8e0eb] bg-white px-5 shadow-[0_8px_18px_rgba(15,23,42,0.04)]">
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-[#98a2b3]">开始日期</div>
                <div className="mt-1 truncate text-[15px] font-semibold text-[#172033]">
                  {customStart || "请选择开始时间"}
                </div>
              </div>
              <button
                className="ml-4 inline-flex shrink-0 items-center gap-3 rounded-[18px] border border-[#d8e0eb] bg-white px-6 py-3 text-[15px] font-semibold text-[#172033]"
                onClick={() => {
                  setCalendarTarget("start");
                  setCalendarMonth(monthKeyFromDate(customStart));
                }}
                type="button"
              >
                <span>{formatCalendarButtonLabel(customStart)}</span>
                <svg aria-hidden="true" className="h-5 w-5 text-[#172033]" fill="none" viewBox="0 0 24 24">
                  <rect x="4" y="5" width="16" height="15" rx="2" stroke="currentColor" strokeWidth="2" />
                  <path d="M8 3v4M16 3v4M4 9h16" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
                </svg>
              </button>
            </div>
            <div className="flex h-[78px] items-center justify-between rounded-[18px] border border-[#d8e0eb] bg-white px-5 shadow-[0_8px_18px_rgba(15,23,42,0.04)]">
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-[#98a2b3]">结束日期</div>
                <div className="mt-1 truncate text-[15px] font-semibold text-[#172033]">
                  {customEnd || "请选择结束时间"}
                </div>
              </div>
              <button
                className="ml-4 inline-flex shrink-0 items-center gap-3 rounded-[18px] border border-[#d8e0eb] bg-white px-6 py-3 text-[15px] font-semibold text-[#172033]"
                onClick={() => {
                  setCalendarTarget("end");
                  setCalendarMonth(monthKeyFromDate(customEnd));
                }}
                type="button"
              >
                <span>{formatCalendarButtonLabel(customEnd)}</span>
                <svg aria-hidden="true" className="h-5 w-5 text-[#172033]" fill="none" viewBox="0 0 24 24">
                  <rect x="4" y="5" width="16" height="15" rx="2" stroke="currentColor" strokeWidth="2" />
                  <path d="M8 3v4M16 3v4M4 9h16" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
                </svg>
              </button>
            </div>
          </div>
        ) : null}

        {timeFilter === "custom" && calendarTarget ? (
          <div className="mt-4 w-full max-w-[460px] rounded-[24px] border border-[#d8e0eb] bg-white p-5 shadow-[0_20px_48px_rgba(15,23,42,0.12)]">
            <div className="flex items-center justify-between">
              <button
                className="text-[16px] font-semibold text-[#172033]"
                onClick={() => setCalendarMonth((prev) => shiftMonth(prev, -1))}
                type="button"
              >
                ←
              </button>
              <div className="text-[16px] font-semibold text-[#172033]">{formatCalendarHeader(calendarMonth)}</div>
              <button
                className="text-[16px] font-semibold text-[#172033]"
                onClick={() => setCalendarMonth((prev) => shiftMonth(prev, 1))}
                type="button"
              >
                →
              </button>
            </div>

            <div className="mt-5 grid grid-cols-7 gap-y-3 text-center text-[14px] font-medium text-[#667085]">
              {weekLabels.map((label) => (
                <div key={label}>{label}</div>
              ))}
            </div>

            <div className="mt-3 grid grid-cols-7 gap-y-2 text-center">
              {calendarDays.map((day) => {
                const selectedValue = calendarTarget === "start" ? customStart : customEnd;
                const isSelected = selectedValue === day.value;
                return (
                  <button
                    key={day.key}
                    className={`mx-auto flex h-10 w-10 items-center justify-center rounded-[12px] text-[15px] font-medium transition ${
                      isSelected
                        ? "bg-[#315efb] text-white shadow-[inset_0_0_0_2px_#1d4ed8]"
                        : day.currentMonth
                          ? "text-[#172033] hover:bg-[#eef4ff]"
                          : "text-[#98a2b3]"
                    }`}
                    onClick={() => {
                      if (calendarTarget === "start") {
                        setCustomStart(day.value);
                      } else {
                        setCustomEnd(day.value);
                      }
                      setPage(1);
                      setCalendarTarget(null);
                    }}
                    type="button"
                  >
                    {day.day}
                  </button>
                );
              })}
            </div>

            <div className="mt-5 flex items-center justify-between">
              <button
                className="text-[16px] font-semibold text-[#315efb]"
                onClick={() => {
                  if (calendarTarget === "start") {
                    setCustomStart("");
                  } else {
                    setCustomEnd("");
                  }
                  setPage(1);
                  setCalendarTarget(null);
                }}
                type="button"
              >
                清除
              </button>
              <button
                className="text-[16px] font-semibold text-[#315efb]"
                onClick={() => {
                  const today = getTodayString();
                  if (calendarTarget === "start") {
                    setCustomStart(today);
                  } else {
                    setCustomEnd(today);
                  }
                  setCalendarMonth(monthKeyFromDate(today));
                  setPage(1);
                  setCalendarTarget(null);
                }}
                type="button"
              >
                今天
              </button>
            </div>
          </div>
        ) : null}
      </Panel>

      <Panel title={currentMonthLabel}>
        <div className="overflow-hidden rounded-[22px] border border-[#e5e7eb] bg-white">
          {loading ? (
            <div className="px-8 py-10 text-[15px] text-[#98a2b3]">加载中...</div>
          ) : null}
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between gap-6 border-b border-[#eef2f6] px-7 py-6 last:border-b-0"
            >
              <div className="flex min-w-0 items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#3b82f6] text-[18px] font-semibold text-white">
                  {(item.title ?? item.model_code ?? "T").slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="truncate text-[17px] font-semibold leading-7 text-[#172033]">
                    {item.title ?? `${item.model_code} 的 API 请求已完成`}
                  </div>
                  <div className="mt-1 truncate text-[14px] text-[#667085]">
                    {item.subtitle ?? `${item.model_code} · ${item.total_tokens.toLocaleString()} tokens · ¥${item.amount}`}
                  </div>
                </div>
              </div>

              <div className="grid shrink-0 grid-cols-[88px_96px] items-center justify-items-end gap-4">
                <div className="w-[88px] text-right text-[14px] font-medium text-[#667085]">
                  {formatRowDate(item.created_at)}
                </div>
                <span className="inline-flex h-10 w-[96px] items-center justify-center whitespace-nowrap rounded-full bg-[#f3f5f9] px-3 text-[13px] font-semibold text-[#4d596a]">
                  {formatBadge(item)}
                </span>
              </div>
            </div>
          ))}
          {!loading && items.length === 0 ? (
            <div className="px-8 py-10 text-[15px] text-[#98a2b3]">暂无使用记录</div>
          ) : null}
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
    </div>
  );
}
