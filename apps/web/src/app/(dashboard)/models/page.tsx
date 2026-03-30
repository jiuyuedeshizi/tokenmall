"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { ModelInfo, PricingItem } from "@/types";

const categoryOptions = [
  { label: "全部", value: "all" },
  { label: "文本模型", value: "text" },
  { label: "图像模型", value: "image" },
  { label: "音频模型", value: "audio" },
  { label: "视频模型", value: "video" },
];

function normalizeCategory(category: string) {
  const value = category.toLowerCase();
  if (value.includes("image")) {
    return "image";
  }
  if (value.includes("audio")) {
    return "audio";
  }
  if (value.includes("video")) {
    return "video";
  }
  return "text";
}

function categoryLabel(category: string) {
  const normalized = normalizeCategory(category);
  if (normalized === "image") {
    return "图像模型";
  }
  if (normalized === "audio") {
    return "音频模型";
  }
  if (normalized === "video") {
    return "视频模型";
  }
  return "文本模型";
}

function renderPricingSummary(items: PricingItem[]) {
  if (!items.length) {
    return ["价格待补充"];
  }
  return items.map((item) => `${item.label}: ¥${item.price}/${item.unit}`);
}

function formatBillingMode(value: string) {
  switch (value) {
    case "per_image":
      return "按张计费";
    case "per_second":
      return "按秒计费";
    case "per_10k_chars":
      return "按万字符计费";
    default:
      return "按Token计费";
  }
}

function ModelIcon() {
  return (
    <div className="flex h-16 w-16 items-center justify-center rounded-[18px] bg-[#e8f0ff] text-[#315efb]">
      <svg aria-hidden="true" className="h-8 w-8" fill="none" viewBox="0 0 24 24">
        <path
          d="M5 7.5A2.5 2.5 0 0 1 7.5 5h9A2.5 2.5 0 0 1 19 7.5v6A2.5 2.5 0 0 1 16.5 16H11l-4 3v-3H7.5A2.5 2.5 0 0 1 5 13.5v-6Z"
          stroke="currentColor"
          strokeWidth="2"
        />
      </svg>
    </div>
  );
}

export default function ModelsPage() {
  const [items, setItems] = useState<ModelInfo[]>([]);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");

  useEffect(() => {
    void apiFetch<ModelInfo[]>("/models").then(setItems);
  }, []);

  const visibleItems = useMemo(() => {
    return items.filter((item) => {
      const matchesCategory =
        activeCategory === "all" || normalizeCategory(item.category) === activeCategory;
      const keyword = search.trim().toLowerCase();
      const matchesSearch =
        !keyword ||
        item.display_name.toLowerCase().includes(keyword) ||
        item.vendor_display_name.toLowerCase().includes(keyword) ||
        item.description.toLowerCase().includes(keyword) ||
        item.tags.some((tag) => tag.toLowerCase().includes(keyword));
      return matchesCategory && matchesSearch;
    });
  }, [activeCategory, items, search]);

  const counts = useMemo(() => {
    return categoryOptions.reduce<Record<string, number>>((acc, option) => {
      acc[option.value] =
        option.value === "all"
          ? items.length
          : items.filter((item) => normalizeCategory(item.category) === option.value).length;
      return acc;
    }, {});
  }, [items]);

  return (
    <Panel title="AI模型库">
      <div className="space-y-7">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="relative max-w-[760px] flex-1">
            <svg
              aria-hidden="true"
              className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#98a2b3]"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
              <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" />
            </svg>
            <input
              className="h-[58px] w-full rounded-[18px] border border-[#d8e0eb] bg-white pl-14 pr-5 text-[18px] text-[#172033] outline-none placeholder:text-[#98a2b3]"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索模型..."
              value={search}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            {categoryOptions.map((option) => {
              const active = activeCategory === option.value;
              return (
                <button
                  key={option.value}
                  className={`rounded-[14px] px-5 py-3 text-[16px] font-semibold transition ${
                    active
                      ? "bg-[#315efb] text-white"
                      : "bg-[#f3f5f9] text-[#4d596a]"
                  }`}
                  onClick={() => setActiveCategory(option.value)}
                  type="button"
                >
                  {option.label} ({counts[option.value] ?? 0})
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          {visibleItems.map((item) => (
            <article
              key={item.model_code}
              className="rounded-[24px] border border-[#dbe3ef] bg-white p-7 shadow-[0_16px_45px_rgba(15,23,42,0.05)]"
            >
              <div className="flex items-start justify-between gap-4">
                <ModelIcon />
                <div className="flex items-center gap-2 text-[16px] font-semibold text-[#172033]">
                  <span className="text-[#f5b90b]">★</span>
                  {item.rating.toFixed(1)}
                </div>
              </div>

              <h3 className="mt-7 text-[24px] font-semibold text-[#172033]">{item.display_name}</h3>
              <div className="mt-2 text-[16px] text-[#667085]">by {item.vendor_display_name}</div>
              <p className="mt-5 min-h-[78px] text-[16px] leading-8 text-[#4d596a]">
                {item.description}
              </p>

              <div className="mt-5">
                <div className="text-[14px] font-semibold text-[#667085]">{formatBillingMode(item.billing_mode)}</div>
                <div className="mt-2 space-y-2 text-[17px] font-semibold">
                  {renderPricingSummary(item.pricing_items).slice(0, 3).map((line, index) => (
                    <div key={`${item.model_code}-${index}`} className={index === 0 ? "text-[#315efb]" : "text-[#16a34a]"}>
                      {line}
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                {item.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-[#f3f5f9] px-3 py-1 text-[14px] text-[#4d596a]"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              <div className="mt-7">
                <Link
                  className="flex h-[52px] w-full items-center justify-center rounded-[16px] bg-[#315efb] text-[18px] font-semibold text-white"
                  href={`/models/item/${item.id}`}
                >
                  开始使用
                </Link>
              </div>

              <div className="mt-4 text-[14px] text-[#98a2b3]">{categoryLabel(item.category)}</div>
            </article>
          ))}
        </div>
      </div>
    </Panel>
  );
}
