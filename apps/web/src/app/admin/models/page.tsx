"use client";

import { useCallback, useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminModel, BailianCatalogItem, ModelPriceSnapshot, PaginatedResponse, PricingItem } from "@/types";

const initialForm = {
  provider: "alibaba-bailian",
  model_code: "",
  model_id: "",
  capability_type: "chat",
  billing_mode: "token",
  display_name: "",
  vendor_display_name: "Alibaba",
  category: "text",
  input_price_per_million: "2.5",
  output_price_per_million: "5",
  pricing_items_json: "",
  rating: "4.8",
  description: "",
  hero_description: "",
  support_features: "多轮对话,代码生成",
  tags: "多轮对话,代码生成",
  example_python: "",
  example_typescript: "",
  example_curl: "",
};

const providerOptions = [
  { label: "阿里百炼", value: "alibaba-bailian", vendor: "Alibaba" },
  { label: "OpenAI", value: "openai", vendor: "OpenAI" },
  { label: "Anthropic", value: "anthropic", vendor: "Anthropic" },
  { label: "DeepSeek", value: "deepseek", vendor: "DeepSeek" },
  { label: "MiniMax", value: "minimax", vendor: "MiniMax" },
  { label: "月之暗面", value: "moonshot", vendor: "Moonshot" },
] as const;

const providerPrefixMap: Record<string, string> = {
  "alibaba-bailian": "dashscope",
  openai: "openai",
  anthropic: "anthropic",
  deepseek: "deepseek",
  minimax: "minimax",
  moonshot: "moonshot",
};

const categoryOptions = [
  { label: "文本模型", value: "text" },
  { label: "图像模型", value: "image" },
  { label: "音频模型", value: "audio" },
  { label: "视频模型", value: "video" },
];

const capabilityOptions = [
  { label: "对话能力", value: "chat" },
  { label: "图像生成", value: "image" },
  { label: "向量嵌入", value: "embedding" },
  { label: "音频能力", value: "audio" },
  { label: "视频能力", value: "video" },
];

const billingModeOptions = [
  { label: "按 Token 计费", value: "token" },
  { label: "按张计费", value: "per_image" },
  { label: "按秒计费", value: "per_second" },
  { label: "按万字符计费", value: "per_10k_chars" },
];

const formFields = [
  { key: "display_name", label: "模型名称", type: "input", placeholder: "例如：Qwen3.5 27B" },
  { key: "vendor_display_name", label: "提供商名称", type: "input", placeholder: "例如：Alibaba" },
  { key: "provider", label: "模型提供商", type: "select" },
  { key: "model_code", label: "平台模型编码", type: "input", placeholder: "例如：qwen-plus" },
  { key: "model_id", label: "真实模型 ID", type: "input", placeholder: "例如：qwen-plus" },
  { key: "capability_type", label: "能力类型", type: "select" },
  { key: "billing_mode", label: "计费模式", type: "select" },
  { key: "category", label: "模型分类", type: "select" },
  { key: "input_price_per_million", label: "输入价格（每百万Token）", type: "input", placeholder: "例如：2.5" },
  { key: "output_price_per_million", label: "输出价格（每百万Token）", type: "input", placeholder: "例如：5" },
  { key: "pricing_items_json", label: "价格项配置", type: "textarea", placeholder: '例如：[{"label":"输入","unit":"元/百万Token","price":"0.8"}]' },
  { key: "rating", label: "评分", type: "input", placeholder: "例如：4.8" },
  { key: "description", label: "卡片简介", type: "textarea", placeholder: "用于模型库列表展示" },
  { key: "hero_description", label: "详情介绍", type: "textarea", placeholder: "用于模型详情页顶部介绍" },
  { key: "support_features", label: "支持功能", type: "input", placeholder: "多个功能用中文逗号分隔" },
  { key: "tags", label: "标签", type: "input", placeholder: "多个标签用中文逗号分隔" },
  { key: "example_python", label: "Python 示例", type: "textarea", placeholder: "可自定义 Python API 使用示例" },
  { key: "example_typescript", label: "TypeScript 示例", type: "textarea", placeholder: "可自定义 TypeScript API 使用示例" },
  { key: "example_curl", label: "cURL 示例", type: "textarea", placeholder: "可自定义 cURL API 使用示例" },
] as const;

function normalizeCsv(value: string) {
  return value
    .split(/[，,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatCategory(value: string) {
  return categoryOptions.find((item) => item.value === value)?.label ?? value;
}

function formatProvider(value: string) {
  return providerOptions.find((item) => item.value === value)?.label ?? value;
}

function formatCapability(value: string) {
  return capabilityOptions.find((item) => item.value === value)?.label ?? value;
}

function formatBillingMode(value: string) {
  return billingModeOptions.find((item) => item.value === value)?.label ?? value;
}

function formatSyncStatus(value?: string) {
  switch (value) {
    case "ready":
      return "已联通";
    case "synced":
      return "已同步";
    case "disabled":
      return "已停用";
    case "error":
      return "同步异常";
    default:
      return "待同步";
  }
}

function formatPriceSource(value?: string) {
  switch (value) {
    case "official_doc":
      return "官方文档";
    case "seed":
      return "系统预置";
    case "preset":
      return "价格映射";
    case "imported":
      return "百炼导入";
    case "manual":
      return "人工维护";
    default:
      return "未标注";
  }
}

function buildLitellmPreview(provider: string, modelId: string) {
  const normalizedModelId = modelId.trim();
  if (!normalizedModelId) {
    return "";
  }
  if (normalizedModelId.includes("/")) {
    return normalizedModelId;
  }
  const prefix = providerPrefixMap[provider] ?? provider;
  return `${prefix}/${normalizedModelId}`;
}

function parsePricingItemsInput(value: string): PricingItem[] {
  const content = value.trim();
  if (!content) {
    return [];
  }
  const parsed = JSON.parse(content);
  if (!Array.isArray(parsed)) {
    throw new Error("价格项配置必须是数组 JSON");
  }
  return parsed.map((item) => ({
    label: String(item.label ?? "").trim(),
    unit: String(item.unit ?? "").trim(),
    price: String(item.price ?? "").trim(),
  })).filter((item) => item.label && item.unit && item.price);
}

function stringifyPricingItems(items: PricingItem[]) {
  return items.length ? JSON.stringify(items, null, 2) : "";
}

function renderPricingSummary(items: PricingItem[]) {
  if (!items.length) {
    return ["暂无价格项"];
  }
  return items.map((item) => `${item.label}：¥${item.price}/${item.unit}`);
}

export default function AdminModelsPage() {
  const [items, setItems] = useState<AdminModel[]>([]);
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [marketItems, setMarketItems] = useState<BailianCatalogItem[]>([]);
  const [marketKeyword, setMarketKeyword] = useState("");
  const [marketCapability, setMarketCapability] = useState("");
  const [marketPage, setMarketPage] = useState(1);
  const [marketTotal, setMarketTotal] = useState(0);
  const [selectedUpstreamIds, setSelectedUpstreamIds] = useState<string[]>([]);
  const [marketLoading, setMarketLoading] = useState(false);
  const [priceHistoryModel, setPriceHistoryModel] = useState<AdminModel | null>(null);
  const [priceHistoryItems, setPriceHistoryItems] = useState<ModelPriceSnapshot[]>([]);
  const [priceHistoryPage, setPriceHistoryPage] = useState(1);
  const [priceHistoryTotal, setPriceHistoryTotal] = useState(0);
  const [priceHistoryLoading, setPriceHistoryLoading] = useState(false);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const marketPageSize = 12;
  const marketTotalPages = Math.max(1, Math.ceil(marketTotal / marketPageSize));
  const priceHistoryPageSize = 8;
  const priceHistoryTotalPages = Math.max(1, Math.ceil(priceHistoryTotal / priceHistoryPageSize));
  const litellmPreview = buildLitellmPreview(form.provider, form.model_id);

  async function load() {
    const result = await apiFetch<PaginatedResponse<AdminModel>>(`/admin/models?page=${page}&page_size=${pageSize}`);
    setItems(result.items);
    setTotal(result.total);
  }

  useEffect(() => {
    let active = true;
    void apiFetch<PaginatedResponse<AdminModel>>(`/admin/models?page=${page}&page_size=${pageSize}`).then((result) => {
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

  function openCreateModal() {
    setEditingId(null);
    setForm(initialForm);
    setIsModalOpen(true);
  }

  const loadBailianModels = useCallback(async (sync = false) => {
    setMarketLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(marketPage),
        page_size: String(marketPageSize),
      });
      if (sync) {
        params.set("sync", "true");
      }
      if (marketKeyword.trim()) {
        params.set("keyword", marketKeyword.trim());
      }
      if (marketCapability) {
        params.set("capability_type", marketCapability);
      }
      const result = await apiFetch<PaginatedResponse<BailianCatalogItem>>(`/admin/bailian-models?${params.toString()}`);
      setMarketItems(result.items);
      setMarketTotal(result.total);
    } finally {
      setMarketLoading(false);
    }
  }, [marketCapability, marketKeyword, marketPage]);

  function openImportModal() {
    setSelectedUpstreamIds([]);
    setMarketPage(1);
    setIsImportModalOpen(true);
  }

  function openEditModal(item: AdminModel) {
    setEditingId(item.id);
    setForm({
      provider: item.provider,
      model_code: item.model_code,
      model_id: item.model_id,
      capability_type: item.capability_type,
      billing_mode: item.billing_mode,
      display_name: item.display_name,
      vendor_display_name: item.vendor_display_name,
      category: item.category,
      input_price_per_million: item.input_price_per_million,
      output_price_per_million: item.output_price_per_million,
      pricing_items_json: stringifyPricingItems(item.pricing_items),
      rating: String(item.rating),
      description: item.description,
      hero_description: item.hero_description,
      support_features: item.support_features.join("，"),
      tags: item.tags.join("，"),
      example_python: item.example_python,
      example_typescript: item.example_typescript,
      example_curl: item.example_curl,
    });
    setIsModalOpen(true);
  }

  function closeModal() {
    setIsModalOpen(false);
    setEditingId(null);
    setForm(initialForm);
    setSubmitting(false);
  }

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        input_price_per_million: Number(form.input_price_per_million),
        output_price_per_million: Number(form.output_price_per_million),
        pricing_items: parsePricingItemsInput(form.pricing_items_json),
        rating: Number(form.rating),
        support_features: normalizeCsv(form.support_features),
        tags: normalizeCsv(form.tags),
        example_python: form.example_python,
        example_typescript: form.example_typescript,
        example_curl: form.example_curl,
      };
      if (editingId) {
        await apiFetch(`/admin/models/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        setNotice("模型已更新");
      } else {
        await apiFetch("/admin/models", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setNotice("模型已创建");
      }
      closeModal();
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (!isImportModalOpen) {
      return;
    }
    void loadBailianModels();
  }, [isImportModalOpen, loadBailianModels]);

  async function handleImportSelected() {
    if (!selectedUpstreamIds.length) {
      setNotice("请至少选择一个模型");
      return;
    }
    setMarketLoading(true);
    try {
      await apiFetch("/admin/bailian-models/import", {
        method: "POST",
        body: JSON.stringify({ upstream_model_ids: selectedUpstreamIds }),
      });
      setNotice(`已导入 ${selectedUpstreamIds.length} 个模型`);
      setIsImportModalOpen(false);
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "导入失败");
    } finally {
      setMarketLoading(false);
    }
  }

  const loadPriceHistory = useCallback(async (modelId: number, pageNumber = 1) => {
    setPriceHistoryLoading(true);
    try {
      const result = await apiFetch<PaginatedResponse<ModelPriceSnapshot>>(
        `/admin/models/${modelId}/price-history?page=${pageNumber}&page_size=${priceHistoryPageSize}`
      );
      setPriceHistoryItems(result.items);
      setPriceHistoryTotal(result.total);
      setPriceHistoryPage(result.page);
    } finally {
      setPriceHistoryLoading(false);
    }
  }, []);

  function openPriceHistory(item: AdminModel) {
    setPriceHistoryModel(item);
    setPriceHistoryPage(1);
    void loadPriceHistory(item.id, 1);
  }

  useEffect(() => {
    if (!priceHistoryModel) {
      return;
    }
    void loadPriceHistory(priceHistoryModel.id, priceHistoryPage);
  }, [priceHistoryModel, priceHistoryPage, loadPriceHistory]);

  return (
    <AuthGuard>
      {({ user }) => (
        <AdminShell user={user}>
          {notice ? (
            <div className="fixed right-8 top-24 z-50 rounded-full bg-[#172033] px-4 py-2 text-[14px] text-white shadow-lg">
              {notice}
            </div>
          ) : null}
          <Panel
            action={
              <div className="flex items-center gap-3">
                <button
                  className="rounded-[16px] border border-[#dbe3ef] bg-white px-5 py-3 text-[15px] font-semibold text-[#172033]"
                  onClick={openImportModal}
                  type="button"
                >
                  从百炼导入
                </button>
                <button
                  className="rounded-[16px] border border-[#dbe3ef] bg-white px-5 py-3 text-[15px] font-semibold text-[#172033]"
                  onClick={() =>
                    void apiFetch("/admin/bailian-models/sync-prices", { method: "POST" })
                      .then(async (result) => {
                        const updated = typeof result === "object" && result && "updated" in result ? Number((result as { updated: number }).updated) : 0;
                        setNotice(updated > 0 ? `价格已同步，更新 ${updated} 个模型` : "价格已同步，当前没有价格变更");
                        await load();
                      })
                      .catch((error) => {
                        setNotice(error instanceof Error ? error.message : "价格同步失败");
                      })
                  }
                  type="button"
                >
                  同步价格
                </button>
                <button
                  className="rounded-[16px] bg-[#315efb] px-5 py-3 text-[15px] font-semibold text-white"
                  onClick={openCreateModal}
                  type="button"
                >
                  手动新增
                </button>
              </div>
            }
            subtitle="维护模型的展示信息、价格、调用 ID 与启停状态。"
            title="模型管理"
          >
            <div className="space-y-4">
              {items.map((item) => (
                <div key={item.id} className="rounded-[24px] border border-[#dbe3ef] bg-white px-6 py-5">
                  <div className="flex items-start justify-between gap-5">
                    <div>
                      <div className="text-[22px] font-semibold text-[#172033]">{item.display_name}</div>
                      <div className="mt-2 text-[14px] text-[#667085]">
                        {item.vendor_display_name} · {item.model_id}
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {item.tags.map((tag) => (
                          <span
                            key={tag}
                            className="rounded-full bg-[#f3f5f9] px-3 py-1 text-[13px] text-[#4d596a]"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="space-y-1 text-[14px] font-semibold">
                        {renderPricingSummary(item.pricing_items).slice(0, 2).map((line, index) => (
                          <div key={`${item.id}-${index}`} className={index === 0 ? "text-[#172033]" : "text-[#16a34a]"}>
                            {line}
                          </div>
                        ))}
                      </div>
                      <div className="mt-2 text-[14px] text-[#667085]">
                        {item.is_active ? "已启用" : "已停用"} · {formatCategory(item.category)} · {formatCapability(item.capability_type)} · {formatBillingMode(item.billing_mode)} · {formatProvider(item.provider)}
                      </div>
                      <div className="mt-2 text-[13px] text-[#98a2b3]">
                        LiteLLM：{item.litellm_model_name || buildLitellmPreview(item.provider, item.model_id)}
                      </div>
                      <div className="mt-2 text-[12px] text-[#98a2b3]">
                        价格来源：{formatPriceSource(item.price_source)}
                        {item.last_price_synced_at ? ` · 最近同步 ${new Date(item.last_price_synced_at).toLocaleString("zh-CN")}` : ""}
                      </div>
                      <div className="mt-2">
                        <span
                          className={`rounded-full px-3 py-1 text-[12px] font-medium ${
                            item.sync_status === "ready"
                              ? "bg-[#e8f7ee] text-[#0f9f57]"
                              : item.sync_status === "error"
                                ? "bg-[#fff1f2] text-[#e11d48]"
                                : item.sync_status === "disabled"
                                  ? "bg-[#f3f5f9] text-[#667085]"
                                  : "bg-[#eef4ff] text-[#315efb]"
                          }`}
                        >
                          {formatSyncStatus(item.sync_status)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <p className="mt-4 text-[15px] leading-7 text-[#4d596a]">{item.hero_description}</p>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {renderPricingSummary(item.pricing_items).map((line) => (
                      <div key={line} className="rounded-[16px] bg-[#f7f9fc] px-4 py-3 text-[13px] text-[#4d596a]">
                        {line}
                      </div>
                    ))}
                  </div>
                  {item.sync_error ? (
                    <div className="mt-4 rounded-[16px] border border-[#ffd6d6] bg-[#fff8f8] px-4 py-3 text-[13px] leading-6 text-[#c2410c]">
                      最近探活结果：{item.sync_error}
                    </div>
                  ) : null}

                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      className="rounded-full border border-[#315efb] px-4 py-2 text-sm font-semibold text-[#315efb]"
                      onClick={() => openEditModal(item)}
                      type="button"
                    >
                      编辑
                    </button>
                    <button
                      className="rounded-full border border-[#dbe3ef] px-4 py-2 text-sm font-semibold text-[#172033]"
                      onClick={() => openPriceHistory(item)}
                      type="button"
                    >
                      价格历史
                    </button>
                    <button
                      className="rounded-full border border-[#dbe3ef] px-4 py-2 text-sm font-semibold text-[#172033]"
                      onClick={() =>
                        void apiFetch(`/admin/models/${item.id}/${item.is_active ? "disable" : "enable"}`, {
                          method: "POST",
                        })
                          .then(async () => {
                            setNotice(item.is_active ? "模型已停用" : "模型已启用");
                            await load();
                          })
                          .catch((error) => {
                            setNotice(error instanceof Error ? error.message : "操作失败");
                          })
                      }
                      type="button"
                    >
                      {item.is_active ? "停用" : "启用"}
                    </button>
                    <button
                      className="rounded-full border border-[#ef4444] px-4 py-2 text-sm font-semibold text-[#ef4444]"
                      onClick={() =>
                        void apiFetch(`/admin/models/${item.id}`, { method: "DELETE" })
                          .then(async () => {
                            setNotice("模型已删除");
                            await load();
                          })
                          .catch((error) => {
                            setNotice(error instanceof Error ? error.message : "删除失败");
                          })
                      }
                      type="button"
                    >
                      删除
                    </button>
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

          {isModalOpen ? (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#172033]/35 px-4">
              <div className="max-h-[88vh] w-full max-w-[880px] overflow-y-auto rounded-[28px] bg-white shadow-[0_32px_80px_rgba(15,23,42,0.18)]">
                <div className="flex items-center justify-between border-b border-[#e5eaf3] px-8 py-6">
                  <div>
                    <h2 className="text-[28px] font-semibold text-[#172033]">
                      {editingId ? "编辑模型" : "新增模型"}
                    </h2>
                    <p className="mt-2 text-[15px] text-[#667085]">
                      请使用中文业务字段填写模型信息，配置完成后会同步到前台模型库与详情页。
                    </p>
                  </div>
                  <button
                    className="text-[30px] leading-none text-[#98a2b3]"
                    onClick={closeModal}
                    type="button"
                  >
                    ×
                  </button>
                </div>

                <div className="grid gap-5 px-8 py-7 md:grid-cols-2">
                  {formFields.map((field) => (
                    <label
                      key={field.key}
                      className={field.type === "textarea" ? "block md:col-span-2" : "block"}
                    >
                      <div className="mb-2 text-[14px] font-medium text-[#4d596a]">{field.label}</div>
                      {field.type === "textarea" ? (
                        <textarea
                          className="min-h-[110px] w-full rounded-[18px] border border-[#dbe3ef] px-4 py-3 text-[15px] text-[#172033] outline-none"
                          onChange={(event) =>
                            setForm((prev) => ({ ...prev, [field.key]: event.target.value }))
                          }
                          placeholder={field.placeholder}
                          value={form[field.key]}
                        />
                      ) : field.type === "select" ? (
                        <select
                          className="h-[50px] w-full rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                          onChange={(event) =>
                            setForm((prev) => {
                              const nextValue = event.target.value;
                              if (field.key === "provider") {
                                const matched = providerOptions.find((item) => item.value === nextValue);
                                return {
                                  ...prev,
                                  provider: nextValue,
                                  vendor_display_name: matched?.vendor ?? prev.vendor_display_name,
                                };
                              }
                              return { ...prev, [field.key]: nextValue };
                            })
                          }
                          value={form[field.key]}
                        >
                          {(field.key === "provider"
                            ? providerOptions
                            : field.key === "capability_type"
                              ? capabilityOptions
                              : field.key === "billing_mode"
                                ? billingModeOptions
                              : categoryOptions
                          ).map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          className="h-[50px] w-full rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                          onChange={(event) =>
                            setForm((prev) => ({ ...prev, [field.key]: event.target.value }))
                          }
                          placeholder={field.placeholder}
                          value={form[field.key]}
                        />
                      )}
                      {field.key === "model_id" ? (
                        <div className="mt-2 rounded-[14px] bg-[#f8fbff] px-4 py-3 text-[12px] leading-6 text-[#667085]">
                          这里只填厂商真实模型名，例如 <span className="font-semibold text-[#172033]">qwen-plus</span>。
                          系统会自动同步成 <span className="font-semibold text-[#315efb]">{litellmPreview || "提供商/模型名"}</span>
                        </div>
                      ) : null}
                      {field.key === "capability_type" ? (
                        <div className="mt-2 rounded-[14px] bg-[#f8fbff] px-4 py-3 text-[12px] leading-6 text-[#667085]">
                          能力类型决定模型探活和调用入口。对话会走 <span className="font-semibold text-[#172033]">chat/completions</span>，图像会走 <span className="font-semibold text-[#172033]">images/generations</span>，向量会走 <span className="font-semibold text-[#172033]">embeddings</span>。
                        </div>
                      ) : null}
                      {field.key === "billing_mode" ? (
                        <div className="mt-2 rounded-[14px] bg-[#f8fbff] px-4 py-3 text-[12px] leading-6 text-[#667085]">
                          计费模式用于前后台展示和后续扩展计费器。文本模型优先选择 <span className="font-semibold text-[#172033]">按 Token 计费</span>。
                        </div>
                      ) : null}
                      {field.key === "pricing_items_json" ? (
                        <div className="mt-2 rounded-[14px] bg-[#f8fbff] px-4 py-3 text-[12px] leading-6 text-[#667085]">
                          这里填写价格项数组 JSON，用于展示文档中的详细价格，例如输入/输出、按张或按秒等计费项。
                        </div>
                      ) : null}
                    </label>
                  ))}
                </div>

                <div className="flex justify-end gap-3 border-t border-[#e5eaf3] px-8 py-5">
                  <button
                    className="rounded-[14px] border border-[#dbe3ef] px-5 py-3 text-[15px] font-semibold text-[#4d596a]"
                    onClick={closeModal}
                    type="button"
                  >
                    取消
                  </button>
                  <button
                    className="rounded-[14px] bg-[#315efb] px-6 py-3 text-[15px] font-semibold text-white disabled:opacity-60"
                    disabled={submitting}
                    onClick={() => void handleSubmit()}
                    type="button"
                  >
                    {submitting ? "保存中..." : editingId ? "保存模型" : "创建模型"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          {isImportModalOpen ? (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#172033]/35 px-4">
              <div className="max-h-[88vh] w-full max-w-[1100px] overflow-y-auto rounded-[28px] bg-white shadow-[0_32px_80px_rgba(15,23,42,0.18)]">
                <div className="flex items-center justify-between border-b border-[#e5eaf3] px-8 py-6">
                  <div>
                    <h2 className="text-[28px] font-semibold text-[#172033]">从百炼导入模型</h2>
                    <p className="mt-2 text-[15px] text-[#667085]">
                      展示当前账号可见的百炼模型，支持搜索、筛选并批量导入到平台模型库。
                    </p>
                  </div>
                  <button className="text-[30px] leading-none text-[#98a2b3]" onClick={() => setIsImportModalOpen(false)} type="button">
                    ×
                  </button>
                </div>

                <div className="space-y-5 px-8 py-6">
                  <div className="flex flex-wrap items-center gap-3">
                    <input
                      className="h-[50px] min-w-[300px] flex-1 rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                      onChange={(event) => setMarketKeyword(event.target.value)}
                      placeholder="搜索模型名称、真实模型 ID 或平台编码"
                      value={marketKeyword}
                    />
                    <select
                      className="h-[50px] rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                      onChange={(event) => {
                        setMarketCapability(event.target.value);
                        setMarketPage(1);
                      }}
                      value={marketCapability}
                    >
                      <option value="">全部能力</option>
                      {capabilityOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <button
                      className="rounded-[16px] border border-[#dbe3ef] px-5 py-3 text-[15px] font-semibold text-[#172033]"
                      onClick={() => void loadBailianModels(true)}
                      type="button"
                    >
                      从百炼刷新
                    </button>
                    <button
                      className="rounded-[16px] border border-[#315efb] px-5 py-3 text-[15px] font-semibold text-[#315efb]"
                      onClick={() => {
                        setMarketPage(1);
                        void loadBailianModels();
                      }}
                      type="button"
                    >
                      搜索
                    </button>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    {marketItems.map((item) => {
                      const checked = selectedUpstreamIds.includes(item.upstream_model_id);
                      return (
                        <button
                          key={item.upstream_model_id}
                          className={`rounded-[22px] border px-5 py-5 text-left transition ${
                            checked ? "border-[#315efb] bg-[#f7faff]" : "border-[#dbe3ef] bg-white"
                          }`}
                          onClick={() =>
                            setSelectedUpstreamIds((prev) =>
                              checked ? prev.filter((value) => value !== item.upstream_model_id) : [...prev, item.upstream_model_id]
                            )
                          }
                          type="button"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <div className="text-[20px] font-semibold text-[#172033]">{item.display_name}</div>
                              <div className="mt-2 text-[14px] text-[#667085]">
                                {item.provider_display_name} · {item.upstream_model_id}
                              </div>
                              <div className="mt-3 flex flex-wrap gap-2">
                                <span className="rounded-full bg-[#f3f5f9] px-3 py-1 text-[12px] text-[#4d596a]">
                                  {formatCapability(item.capability_type)}
                                </span>
                                <span className="rounded-full bg-[#f3f5f9] px-3 py-1 text-[12px] text-[#4d596a]">
                                  {formatCategory(item.category)}
                                </span>
                                {item.is_imported ? (
                                  <span className="rounded-full bg-[#e8f7ee] px-3 py-1 text-[12px] text-[#0f9f57]">
                                    已导入
                                  </span>
                                ) : null}
                              </div>
                            </div>
                            <div className="pt-1">
                              <input checked={checked} readOnly type="checkbox" />
                            </div>
                          </div>
                          <p className="mt-4 min-h-[44px] text-[14px] leading-6 text-[#4d596a]">
                            {item.description || "该模型来自百炼账号可见列表，暂无更详细说明。"}
                          </p>
                          <div className="mt-4 flex flex-wrap gap-2">
                            <span className="rounded-full bg-[#eef4ff] px-3 py-1 text-[12px] text-[#315efb]">
                              {formatBillingMode(item.billing_mode)}
                            </span>
                            {renderPricingSummary(item.pricing_items).map((line) => (
                              <span key={line} className="rounded-full bg-[#f7f9fc] px-3 py-1 text-[12px] text-[#4d596a]">
                                {line}
                              </span>
                            ))}
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="text-[14px] text-[#667085]">
                      共 {marketTotal} 条，当前第 {marketPage} / {marketTotalPages} 页
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        className="rounded-[14px] border border-[#d8e0eb] px-4 py-2 text-[14px] font-semibold text-[#172033] disabled:opacity-50"
                        disabled={marketPage <= 1}
                        onClick={() => setMarketPage((prev) => Math.max(1, prev - 1))}
                        type="button"
                      >
                        上一页
                      </button>
                      <button
                        className="rounded-[14px] border border-[#d8e0eb] px-4 py-2 text-[14px] font-semibold text-[#172033] disabled:opacity-50"
                        disabled={marketPage >= marketTotalPages}
                        onClick={() => setMarketPage((prev) => Math.min(marketTotalPages, prev + 1))}
                        type="button"
                      >
                        下一页
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3 border-t border-[#e5eaf3] px-8 py-5">
                  <button
                    className="rounded-[14px] border border-[#dbe3ef] px-5 py-3 text-[15px] font-semibold text-[#4d596a]"
                    onClick={() => setIsImportModalOpen(false)}
                    type="button"
                  >
                    取消
                  </button>
                  <button
                    className="rounded-[14px] bg-[#315efb] px-6 py-3 text-[15px] font-semibold text-white disabled:opacity-60"
                    disabled={marketLoading}
                    onClick={() => void handleImportSelected()}
                    type="button"
                  >
                    {marketLoading ? "处理中..." : `导入已选 ${selectedUpstreamIds.length} 个模型`}
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          {priceHistoryModel ? (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#172033]/35 px-4">
              <div className="max-h-[84vh] w-full max-w-[860px] overflow-y-auto rounded-[28px] bg-white shadow-[0_32px_80px_rgba(15,23,42,0.18)]">
                <div className="flex items-center justify-between border-b border-[#e5eaf3] px-8 py-6">
                  <div>
                    <h2 className="text-[26px] font-semibold text-[#172033]">价格历史</h2>
                    <p className="mt-2 text-[14px] text-[#667085]">
                      {priceHistoryModel.display_name} · {priceHistoryModel.model_code}
                    </p>
                  </div>
                  <button className="text-[30px] leading-none text-[#98a2b3]" onClick={() => setPriceHistoryModel(null)} type="button">
                    ×
                  </button>
                </div>
                <div className="space-y-4 px-8 py-6">
                  {priceHistoryItems.map((item) => (
                    <div key={item.id} className="rounded-[20px] border border-[#dbe3ef] bg-white px-5 py-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="text-[15px] font-semibold text-[#172033]">{formatBillingMode(priceHistoryModel.billing_mode)}</div>
                          <div className="mt-2 text-[13px] text-[#667085]">
                            来源：{formatPriceSource(item.price_source)} · {new Date(item.created_at).toLocaleString("zh-CN")}
                          </div>
                        </div>
                      </div>
                      <div className="mt-3 text-[13px] leading-6 text-[#4d596a]">
                        输入 ¥{item.input_price_per_million} / 输出 ¥{item.output_price_per_million} · {item.note || "无备注"}
                      </div>
                    </div>
                  ))}
                  {priceHistoryLoading ? <div className="text-[14px] text-[#667085]">加载中...</div> : null}
                </div>
                <div className="flex items-center justify-between border-t border-[#e5eaf3] px-8 py-5">
                  <div className="text-[14px] text-[#667085]">
                    共 {priceHistoryTotal} 条，当前第 {priceHistoryPage} / {priceHistoryTotalPages} 页
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      className="rounded-[14px] border border-[#d8e0eb] px-4 py-2 text-[14px] font-semibold text-[#172033] disabled:opacity-50"
                      disabled={priceHistoryPage <= 1}
                      onClick={() => setPriceHistoryPage((prev) => Math.max(1, prev - 1))}
                      type="button"
                    >
                      上一页
                    </button>
                    <button
                      className="rounded-[14px] border border-[#d8e0eb] px-4 py-2 text-[14px] font-semibold text-[#172033] disabled:opacity-50"
                      disabled={priceHistoryPage >= priceHistoryTotalPages}
                      onClick={() => setPriceHistoryPage((prev) => Math.min(priceHistoryTotalPages, prev + 1))}
                      type="button"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </AdminShell>
      )}
    </AuthGuard>
  );
}
