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
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
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
                          className={`min-h-[110px] w-full rounded-[18px] border border-[#dbe3ef] px-4 py-3 text-[15px] text-[#172033] outline-none ${
                            field.key.startsWith("example_") ? "font-mono leading-7" : ""
                          }`}
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
                          这里只填透明代理实际转发用的上游模型 ID，例如 <span className="font-semibold text-[#172033]">qwen-plus</span>。
                          当前系统要求它与平台模型编码保持一致。
                        </div>
                      ) : null}
                      {field.key === "capability_type" ? (
                        <div className="mt-2 rounded-[14px] bg-[#f8fbff] px-4 py-3 text-[12px] leading-6 text-[#667085]">
                          能力类型决定模型探活和调用入口。对话会走 <span className="font-semibold text-[#172033]">chat/completions</span>，图像/音频会走 <span className="font-semibold text-[#172033]">multimodal-generation</span>，视频会走 <span className="font-semibold text-[#172033]">video-synthesis</span>，向量会走 <span className="font-semibold text-[#172033]">embeddings</span>。
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
                      {field.key.startsWith("example_") ? (
                        <div className="mt-2 rounded-[14px] bg-[#f8fbff] px-4 py-3 text-[12px] leading-6 text-[#667085]">
                          详情页会优先显示这里配置的示例；留空时，系统会自动回退到后台预置示例。建议在这里维护更贴近业务场景的调用代码。
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
        </AdminShell>
      )}
    </AuthGuard>
  );
}
