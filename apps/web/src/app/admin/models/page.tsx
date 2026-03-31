"use client";

import { useEffect, useState } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { AdminShell } from "@/components/admin-shell";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";
import type { AdminModel, PaginatedResponse, PricingItem } from "@/types";

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
  pricing_items: [] as PricingItem[],
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

const pricingPresetOptions = [
  { label: "输入", unit: "元/百万Token" },
  { label: "输出", unit: "元/百万Token" },
  { label: "图片生成", unit: "元/张" },
  { label: "语音识别", unit: "元/每秒" },
  { label: "语音合成", unit: "元/每万字符" },
  { label: "720P 无声", unit: "元/每秒" },
  { label: "1080P 无声", unit: "元/每秒" },
  { label: "720P 有声", unit: "元/每秒" },
  { label: "1080P 有声", unit: "元/每秒" },
  { label: "文本处理", unit: "元/每万字符" },
] as const;

const CUSTOM_PRICING_LABEL = "__custom__";

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

function normalizePricingItems(items: PricingItem[]) {
  return items
    .map((item) => ({
      label: String(item.label ?? "").trim(),
      unit: String(item.unit ?? "").trim(),
      price: String(item.price ?? "").trim(),
    }))
    .filter((item) => item.label && item.unit && item.price);
}

function getPresetUnit(label: string) {
  return pricingPresetOptions.find((option) => option.label === label)?.unit ?? "";
}

function isPresetPricingLabel(label: string) {
  return pricingPresetOptions.some((option) => option.label === label);
}

function getDefaultPricingItems(
  billingMode: string,
  inputPricePerMillion: string,
  outputPricePerMillion: string,
) {
  switch (billingMode) {
    case "per_image":
      return [{ label: "图片生成", unit: "元/张", price: outputPricePerMillion || "0" }];
    case "per_second":
      return [
        { label: "720P 无声", unit: "元/每秒", price: outputPricePerMillion || "0" },
        { label: "1080P 无声", unit: "元/每秒", price: outputPricePerMillion || "0" },
      ];
    case "per_10k_chars":
      return [{ label: "文本处理", unit: "元/每万字符", price: outputPricePerMillion || "0" }];
    default:
      return [
        { label: "输入", unit: "元/百万Token", price: inputPricePerMillion || "0" },
        { label: "输出", unit: "元/百万Token", price: outputPricePerMillion || "0" },
      ];
  }
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
  const [showExampleSection, setShowExampleSection] = useState(false);
  const [notice, setNotice] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const inputClass = "h-[50px] w-full rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none";
  const textareaClass = "min-h-[110px] w-full rounded-[18px] border border-[#dbe3ef] px-4 py-3 text-[15px] text-[#172033] outline-none";

  function updateFormField<Key extends keyof typeof initialForm>(key: Key, value: (typeof initialForm)[Key]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function renderFieldHint(content: React.ReactNode) {
    return (
      <div className="mt-2 rounded-[14px] bg-[#f8fbff] px-4 py-3 text-[12px] leading-6 text-[#667085]">
        {content}
      </div>
    );
  }

  function renderSection(title: string, description: string, content: React.ReactNode) {
    return (
      <section className="rounded-[24px] border border-[#e5eaf3] bg-[#fcfdff] p-5">
        <div className="mb-4">
          <h3 className="text-[18px] font-semibold text-[#172033]">{title}</h3>
          <p className="mt-1 text-[13px] leading-6 text-[#667085]">{description}</p>
        </div>
        <div className="grid gap-5 md:grid-cols-2">{content}</div>
      </section>
    );
  }

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
    setShowExampleSection(false);
    setIsModalOpen(true);
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
      pricing_items: item.pricing_items,
      rating: String(item.rating),
      description: item.description,
      hero_description: item.hero_description,
      support_features: item.support_features.join("，"),
      tags: item.tags.join("，"),
      example_python: item.example_python,
      example_typescript: item.example_typescript,
      example_curl: item.example_curl,
    });
    setShowExampleSection(Boolean(item.example_python || item.example_typescript || item.example_curl));
    setIsModalOpen(true);
  }

  function closeModal() {
    setIsModalOpen(false);
    setEditingId(null);
    setForm(initialForm);
    setShowExampleSection(false);
    setSubmitting(false);
  }

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        input_price_per_million: Number(form.input_price_per_million),
        output_price_per_million: Number(form.output_price_per_million),
        pricing_items: normalizePricingItems(
          form.pricing_items.length
            ? form.pricing_items
            : getDefaultPricingItems(
                form.billing_mode,
                form.input_price_per_million,
                form.output_price_per_million,
              )
        ),
        rating: Number(form.rating),
        description: form.description.trim(),
        hero_description: form.hero_description.trim() || form.description.trim(),
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

  function resolveActivePricingItems(currentForm = form) {
    return currentForm.pricing_items.length
      ? currentForm.pricing_items
      : getDefaultPricingItems(
          currentForm.billing_mode,
          currentForm.input_price_per_million,
          currentForm.output_price_per_million,
        );
  }

  function updatePricingItems(updater: (items: PricingItem[]) => PricingItem[]) {
    setForm((prev) => ({
      ...prev,
      pricing_items: updater(resolveActivePricingItems(prev)),
    }));
  }

  function createSuggestedPricingItem(billingMode: string) {
    switch (billingMode) {
      case "per_image":
        return { label: "图片生成", unit: "元/张", price: "" };
      case "per_second":
        return { label: "720P 无声", unit: "元/每秒", price: "" };
      case "per_10k_chars":
        return { label: "文本处理", unit: "元/每万字符", price: "" };
      default:
        return { label: "输入", unit: "元/百万Token", price: "" };
    }
  }

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
                        {item.supports_multimodal_chat ? (
                          <span className="rounded-full bg-[#e8f7ee] px-3 py-1 text-[13px] font-semibold text-[#0f9f57]">
                            已支持多模态 Chat
                          </span>
                        ) : null}
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
              <div className="max-h-[88vh] w-full max-w-[980px] overflow-y-auto rounded-[28px] bg-white shadow-[0_32px_80px_rgba(15,23,42,0.18)]">
                <div className="flex items-center justify-between border-b border-[#e5eaf3] px-8 py-6">
                  <div>
                    <h2 className="text-[28px] font-semibold text-[#172033]">
                      {editingId ? "编辑模型" : "新增模型"}
                    </h2>
                    <p className="mt-2 text-[15px] text-[#667085]">
                      表单已按基础信息、计费配置、展示文案和示例代码分组，优先填写必要字段即可。
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

                <div className="space-y-5 px-8 py-7">
                  <div className="rounded-[22px] border border-[#dbe3ef] bg-[#f7f9fc] px-5 py-4">
                    <div className="flex flex-wrap items-center gap-2 text-[13px] text-[#667085]">
                      <span className="rounded-full bg-white px-3 py-1 text-[#172033]">平台编码：{form.model_code || "未填写"}</span>
                      <span className="rounded-full bg-white px-3 py-1 text-[#172033]">上游 ID：{form.model_id || "未填写"}</span>
                      <span className="rounded-full bg-white px-3 py-1 text-[#172033]">计费方式：{formatBillingMode(form.billing_mode)}</span>
                    </div>
                  </div>

                  {renderSection(
                    "基础信息",
                    "先确定展示名称、供应商和模型编码，这一组是最常编辑的基础字段。",
                    <>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">模型名称</div>
                        <input
                          className={inputClass}
                          onChange={(event) => updateFormField("display_name", event.target.value)}
                          placeholder="例如：Qwen3.5 27B"
                          value={form.display_name}
                        />
                      </label>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">模型提供商</div>
                        <select
                          className={inputClass}
                          onChange={(event) => {
                            const nextValue = event.target.value;
                            const matched = providerOptions.find((item) => item.value === nextValue);
                            setForm((prev) => ({
                              ...prev,
                              provider: nextValue,
                              vendor_display_name: matched?.vendor ?? prev.vendor_display_name,
                            }));
                          }}
                          value={form.provider}
                        >
                          {providerOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">厂商展示名</div>
                        <input
                          className={inputClass}
                          onChange={(event) => updateFormField("vendor_display_name", event.target.value)}
                          placeholder="例如：Alibaba"
                          value={form.vendor_display_name}
                        />
                        {renderFieldHint("通常保持系统自动带出的默认值即可，只有前台展示需要特殊文案时再修改。")}
                      </label>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">模型分类</div>
                        <select
                          className={inputClass}
                          onChange={(event) => updateFormField("category", event.target.value)}
                          value={form.category}
                        >
                          {categoryOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">平台模型编码</div>
                        <input
                          className={inputClass}
                          onChange={(event) => updateFormField("model_code", event.target.value)}
                          placeholder="例如：qwen-plus"
                          value={form.model_code}
                        />
                      </label>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">上游模型 ID</div>
                        <input
                          className={inputClass}
                          onChange={(event) => updateFormField("model_id", event.target.value)}
                          placeholder="例如：qwen-plus"
                          value={form.model_id}
                        />
                        {renderFieldHint(
                          <>
                            透明代理当前要求 <span className="font-semibold text-[#172033]">平台模型编码</span> 与 <span className="font-semibold text-[#172033]">上游模型 ID</span> 保持一致。
                          </>
                        )}
                      </label>
                    </>
                  )}

                  {renderSection(
                    "能力与计费",
                    "这一组决定模型的调用入口、价格展示方式和后台筛选标签。",
                    <>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">能力类型</div>
                        <select
                          className={inputClass}
                          onChange={(event) => updateFormField("capability_type", event.target.value)}
                          value={form.capability_type}
                        >
                          {capabilityOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        {renderFieldHint(
                          <>
                            对话走 <span className="font-semibold text-[#172033]">chat/completions</span>，图像/音频走 <span className="font-semibold text-[#172033]">multimodal-generation</span>，视频走 <span className="font-semibold text-[#172033]">video-synthesis</span>，向量走 <span className="font-semibold text-[#172033]">embeddings</span>。
                          </>
                        )}
                      </label>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">评分</div>
                        <input
                          className={inputClass}
                          onChange={(event) => updateFormField("rating", event.target.value)}
                          placeholder="例如：4.8"
                          value={form.rating}
                        />
                      </label>
                    </>
                  )}

                  {renderSection(
                    "价格信息",
                    "计费模式和价格展示都放在这里维护。大多数情况下不需要写 JSON，按行添加价格项就可以。",
                    <>
                      <label className="block md:col-span-2">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">计费模式</div>
                        <select
                          className={inputClass}
                          onChange={(event) => {
                            const nextBillingMode = event.target.value;
                            setForm((prev) => ({
                              ...prev,
                              billing_mode: nextBillingMode,
                              pricing_items: getDefaultPricingItems(
                                nextBillingMode,
                                prev.input_price_per_million,
                                prev.output_price_per_million,
                              ),
                            }));
                          }}
                          value={form.billing_mode}
                        >
                          {billingModeOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        {renderFieldHint("文本模型通常选择按 Token 计费；图片、音频、视频模型优先按张、按秒或按万字符维护。")}
                      </label>
                      {form.billing_mode === "token" ? (
                        <>
                          <label className="block">
                            <div className="mb-2 text-[14px] font-medium text-[#4d596a]">输入价格（每百万Token）</div>
                            <input
                              className={inputClass}
                              onChange={(event) => {
                                const nextValue = event.target.value;
                                setForm((prev) => ({
                                  ...prev,
                                  input_price_per_million: nextValue,
                                  pricing_items:
                                    prev.billing_mode === "token" && prev.pricing_items.length <= 2
                                      ? prev.pricing_items.map((item) =>
                                          item.label === "输入" ? { ...item, price: nextValue } : item
                                        )
                                      : prev.pricing_items,
                                }));
                              }}
                              placeholder="例如：2.5"
                              value={form.input_price_per_million}
                            />
                          </label>
                          <label className="block">
                            <div className="mb-2 text-[14px] font-medium text-[#4d596a]">输出价格（每百万Token）</div>
                            <input
                              className={inputClass}
                              onChange={(event) => {
                                const nextValue = event.target.value;
                                setForm((prev) => ({
                                  ...prev,
                                  output_price_per_million: nextValue,
                                  pricing_items:
                                    prev.pricing_items.length <= 2
                                      ? prev.pricing_items.map((item) =>
                                          item.label === "输出" ? { ...item, price: nextValue } : item
                                        )
                                      : prev.pricing_items,
                                }));
                              }}
                              placeholder="例如：5"
                              value={form.output_price_per_million}
                            />
                          </label>
                        </>
                      ) : null}
                      <label className="block md:col-span-2">
                        <div className="mb-3 flex items-center justify-between">
                          <div className="text-[14px] font-medium text-[#4d596a]">价格项配置</div>
                          <button
                            className="rounded-full border border-[#dbe3ef] px-3 py-1 text-[12px] font-semibold text-[#315efb]"
                            onClick={() => updatePricingItems((items) => [...items, createSuggestedPricingItem(form.billing_mode)])}
                            type="button"
                          >
                            添加价格项
                          </button>
                        </div>
                        <div className="space-y-3">
                          {resolveActivePricingItems().map((item, index) => {
                            const isCustom = !isPresetPricingLabel(item.label);
                            const selectValue = isCustom ? CUSTOM_PRICING_LABEL : item.label;

                            return (
                            <div
                              key={`${item.label}-${index}`}
                              className="grid gap-3 rounded-[18px] border border-[#dbe3ef] bg-white p-4 md:grid-cols-[1.2fr_1fr_0.8fr_auto]"
                            >
                              <div className="space-y-3">
                                <select
                                  className={inputClass}
                                  onChange={(event) =>
                                    updatePricingItems((items) =>
                                      items.map((current, currentIndex) =>
                                        currentIndex === index
                                          ? event.target.value === CUSTOM_PRICING_LABEL
                                            ? { ...current, label: current.label && isPresetPricingLabel(current.label) ? "" : current.label, unit: current.unit && isPresetPricingLabel(current.label) ? "" : current.unit }
                                            : {
                                                ...current,
                                                label: event.target.value,
                                                unit: getPresetUnit(event.target.value),
                                              }
                                          : current
                                      )
                                    )
                                  }
                                  value={selectValue}
                                >
                                  {pricingPresetOptions.map((option) => (
                                    <option key={option.label} value={option.label}>
                                      {option.label}
                                    </option>
                                  ))}
                                  <option value={CUSTOM_PRICING_LABEL}>自定义</option>
                                </select>
                                {isCustom ? (
                                  <input
                                    className={inputClass}
                                    onChange={(event) =>
                                      updatePricingItems((items) =>
                                        items.map((current, currentIndex) =>
                                          currentIndex === index ? { ...current, label: event.target.value } : current
                                        )
                                      )
                                    }
                                    placeholder="自定义名称，例如：4K 有声"
                                    value={item.label}
                                  />
                                ) : null}
                              </div>
                              <div className="space-y-3">
                                <input
                                  className={`${inputClass} ${isCustom ? "" : "bg-[#f7f9fc] text-[#667085]"}`}
                                  onChange={(event) =>
                                    updatePricingItems((items) =>
                                      items.map((current, currentIndex) =>
                                        currentIndex === index ? { ...current, unit: event.target.value } : current
                                      )
                                    )
                                  }
                                  placeholder="单位，例如：元/每秒"
                                  readOnly={!isCustom}
                                  value={item.unit}
                                />
                                {!isCustom ? (
                                  <div className="px-1 text-[12px] text-[#98a2b3]">预设项会自动带出单位。</div>
                                ) : null}
                              </div>
                              <input
                                className={inputClass}
                                onChange={(event) =>
                                  updatePricingItems((items) =>
                                    items.map((current, currentIndex) =>
                                      currentIndex === index ? { ...current, price: event.target.value } : current
                                    )
                                  )
                                }
                                placeholder="价格"
                                value={item.price}
                              />
                              <button
                                className="rounded-[14px] border border-[#ef4444] px-3 py-2 text-[13px] font-semibold text-[#ef4444]"
                                onClick={() => updatePricingItems((items) => items.filter((_, currentIndex) => currentIndex !== index))}
                                type="button"
                              >
                                删除
                              </button>
                            </div>
                          );
                          })}
                        </div>
                        {renderFieldHint("优先选择预设名称，系统会自动带出单位；只有遇到特殊档位时再切到“自定义”。大多数情况下你只需要调整价格。")}
                      </label>
                    </>
                  )}

                  {renderSection(
                    "展示文案",
                    "这里是前台模型卡片和详情页直接会看到的内容，能少填就别重复填。",
                    <>
                      <label className="block md:col-span-2">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">卡片简介</div>
                        <textarea
                          className={textareaClass}
                          onChange={(event) => updateFormField("description", event.target.value)}
                          placeholder="用于模型库列表展示"
                          value={form.description}
                        />
                      </label>
                      <label className="block md:col-span-2">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">详情介绍</div>
                        <textarea
                          className={textareaClass}
                          onChange={(event) => updateFormField("hero_description", event.target.value)}
                          placeholder="留空时默认使用卡片简介"
                          value={form.hero_description}
                        />
                        {renderFieldHint("如果详情页顶部文案和列表简介差不多，可以直接留空，保存时会自动沿用卡片简介。")}
                      </label>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">支持功能</div>
                        <input
                          className={inputClass}
                          onChange={(event) => updateFormField("support_features", event.target.value)}
                          placeholder="多个功能用中文逗号分隔"
                          value={form.support_features}
                        />
                      </label>
                      <label className="block">
                        <div className="mb-2 text-[14px] font-medium text-[#4d596a]">标签</div>
                        <input
                          className={inputClass}
                          onChange={(event) => updateFormField("tags", event.target.value)}
                          placeholder="多个标签用中文逗号分隔"
                          value={form.tags}
                        />
                      </label>
                    </>
                  )}

                  <section className="rounded-[24px] border border-[#e5eaf3] bg-[#fcfdff] p-5">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <h3 className="text-[18px] font-semibold text-[#172033]">示例代码</h3>
                        <p className="mt-1 text-[13px] leading-6 text-[#667085]">
                          只在需要覆盖默认示例时填写。留空会自动回退到系统内置示例。
                        </p>
                      </div>
                      <button
                        className="rounded-full border border-[#dbe3ef] px-4 py-2 text-[13px] font-semibold text-[#315efb]"
                        onClick={() => setShowExampleSection((prev) => !prev)}
                        type="button"
                      >
                        {showExampleSection ? "收起示例代码" : "展开示例代码"}
                      </button>
                    </div>
                    {showExampleSection ? (
                      <div className="mt-5 grid gap-5 md:grid-cols-2">
                        <label className="block md:col-span-2">
                          <div className="mb-2 text-[14px] font-medium text-[#4d596a]">Python 示例</div>
                          <textarea
                            className={`${textareaClass} font-mono leading-7`}
                            onChange={(event) => updateFormField("example_python", event.target.value)}
                            placeholder="可自定义 Python API 使用示例"
                            value={form.example_python}
                          />
                        </label>
                        <label className="block md:col-span-2">
                          <div className="mb-2 text-[14px] font-medium text-[#4d596a]">TypeScript 示例</div>
                          <textarea
                            className={`${textareaClass} font-mono leading-7`}
                            onChange={(event) => updateFormField("example_typescript", event.target.value)}
                            placeholder="可自定义 TypeScript API 使用示例"
                            value={form.example_typescript}
                          />
                        </label>
                        <label className="block md:col-span-2">
                          <div className="mb-2 text-[14px] font-medium text-[#4d596a]">cURL 示例</div>
                          <textarea
                            className={`${textareaClass} font-mono leading-7`}
                            onChange={(event) => updateFormField("example_curl", event.target.value)}
                            placeholder="可自定义 cURL API 使用示例"
                            value={form.example_curl}
                          />
                        </label>
                      </div>
                    ) : null}
                  </section>
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
        </AdminShell>
      )}
    </AuthGuard>
  );
}
