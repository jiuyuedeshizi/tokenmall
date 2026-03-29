"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { apiFetch } from "@/lib/api";
import type { ModelInfo } from "@/types";

function formatPrice(value: string) {
  return Number(value).toLocaleString("zh-CN", {
    maximumFractionDigits: 2,
  });
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

function SideCard({
  title,
  children,
  tint = "white",
}: {
  title: string;
  children: ReactNode;
  tint?: "white" | "blue";
}) {
  return (
    <section
      className={`rounded-[22px] border p-8 ${
        tint === "blue"
          ? "border-[#dce9ff] bg-[#eef4ff]"
          : "border-[#e5eaf3] bg-white"
      }`}
    >
      <h3 className="text-[22px] font-semibold text-[#172033]">{title}</h3>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function CodeBlock({
  language,
  code,
  onCopy,
}: {
  language: string;
  code: string;
  onCopy: () => void;
}) {
  return (
    <div className="mt-8 first:mt-0">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[18px] font-semibold text-[#172033]">{language}</div>
        <button
          className="flex items-center gap-2 text-[14px] font-semibold text-[#315efb]"
          onClick={onCopy}
          type="button"
        >
          <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
            <rect height="14" rx="2" stroke="currentColor" strokeWidth="2" width="14" x="8" y="6" />
            <path
              d="M16 4H6a2 2 0 0 0-2 2v10"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
            />
          </svg>
          复制
        </button>
      </div>
      <pre className="overflow-x-auto rounded-[18px] bg-[#f4f6fb] p-8 text-[14px] leading-8 text-[#172033]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export default function ModelDetailPage() {
  const params = useParams<{ id: string }>();
  const [item, setItem] = useState<ModelInfo | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!params?.id) {
      return;
    }
    void apiFetch<ModelInfo>(`/models/item/${params.id}`).then(setItem);
  }, [params?.id]);

  useEffect(() => {
    if (!notice) {
      return;
    }
    const timer = window.setTimeout(() => setNotice(""), 1800);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const snippets = useMemo(() => {
    if (!item) {
      return [];
    }

    const baseUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}/api`
        : (process.env.NEXT_PUBLIC_API_URL ?? "/api");
    const python = item.example_python || `import requests

url = "${baseUrl}/v1/chat/completions"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}
data = {
    "model": "${item.model_id}",
    "messages": [{"role": "user", "content": "你好"}]
}

response = requests.post(url, headers=headers, json=data)
print(response.json())`;

    const typescript = item.example_typescript || `const response = await fetch('${baseUrl}/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: '${item.model_id}',
    messages: [{ role: 'user', content: '你好' }]
  })
});

const data = await response.json();
console.log(data);`;

    const curl = item.example_curl || `curl -X POST ${baseUrl}/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${item.model_id}",
    "messages": [{"role": "user", "content": "你好"}]
  }'`;

    return [
      { language: "Python", code: python },
      { language: "TypeScript", code: typescript },
      { language: "cURL", code: curl },
    ];
  }, [item]);

  async function copyText(value: string) {
    await navigator.clipboard.writeText(value);
    setNotice("已复制");
  }

  function scrollToExamples() {
    document.getElementById("api-examples")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (!item) {
    return (
      <section className="rounded-[32px] border border-[var(--line)] bg-white p-10 shadow-[var(--card-shadow)]">
        <div className="text-[16px] text-[#98a2b3]">加载模型信息中...</div>
      </section>
    );
  }

  return (
    <section className="rounded-[32px] border border-[var(--line)] bg-white p-8 shadow-[var(--card-shadow)]">
      {notice ? (
        <div className="fixed right-8 top-24 z-50 rounded-full bg-[#172033] px-4 py-2 text-[14px] text-white shadow-lg">
          {notice}
        </div>
      ) : null}

      <Link
        className="inline-flex items-center gap-2 text-[16px] font-semibold text-[#315efb]"
        href="/models"
      >
        <span className="text-[20px]">←</span>
        返回模型库
      </Link>

      <div className="mt-8 grid gap-8 xl:grid-cols-[1.9fr_0.9fr]">
        <div className="space-y-8">
          <section className="rounded-[22px] border border-[#e5eaf3] bg-white p-8">
            <div className="flex items-start justify-between gap-6">
              <div className="flex items-start gap-5">
                <ModelIcon />
                <div>
                  <h1 className="text-[30px] font-semibold text-[#172033]">{item.display_name}</h1>
                  <div className="mt-2 text-[18px] text-[#667085]">by {item.vendor_display_name}</div>
                </div>
              </div>
              <button
                className="h-[52px] rounded-[16px] bg-[#315efb] px-8 text-[18px] font-semibold text-white"
                onClick={scrollToExamples}
                type="button"
              >
                立即试用
              </button>
            </div>
            <p className="mt-8 text-[18px] leading-9 text-[#4d596a]">{item.hero_description}</p>
          </section>

          <section className="rounded-[22px] border border-[#e5eaf3] bg-white p-8">
            <h2 className="text-[22px] font-semibold text-[#172033]">价格信息</h2>
            <div className="mt-7 grid gap-5 md:grid-cols-2">
              <div className="rounded-[18px] bg-[#eef4ff] p-6">
                <div className="text-[16px] text-[#4d596a]">输入价格</div>
                <div className="mt-4 text-[28px] font-semibold text-[#315efb]">
                  ¥{formatPrice(item.input_price_per_million)}/百万Token
                </div>
              </div>
              <div className="rounded-[18px] bg-[#edf9f0] p-6">
                <div className="text-[16px] text-[#4d596a]">输出价格</div>
                <div className="mt-4 text-[28px] font-semibold text-[#16a34a]">
                  ¥{formatPrice(item.output_price_per_million)}/百万Token
                </div>
              </div>
            </div>
          </section>

          <section
            className="rounded-[22px] border border-[#e5eaf3] bg-white p-8"
            id="api-examples"
          >
            <h2 className="text-[22px] font-semibold text-[#172033]">API 使用示例</h2>
            <div className="mt-6">
              {snippets.map((snippet) => (
                <CodeBlock
                  key={snippet.language}
                  code={snippet.code}
                  language={snippet.language}
                  onCopy={() => void copyText(snippet.code)}
                />
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-8">
          <SideCard title="模型信息">
            <div className="space-y-7 text-[16px]">
              <div>
                <div className="text-[#667085]">提供商</div>
                <div className="mt-2 text-[18px] font-semibold text-[#172033]">
                  {item.vendor_display_name}
                </div>
              </div>
              <div>
                <div className="text-[#667085]">模型ID</div>
                <div className="mt-2 break-all text-[18px] font-semibold text-[#172033]">
                  {item.model_id}
                </div>
              </div>
              <div>
                <div className="text-[#667085]">评分</div>
                <div className="mt-2 text-[18px] font-semibold text-[#172033]">
                  <span className="mr-1 text-[#f5b90b]">★</span>
                  {item.rating.toFixed(1)}
                </div>
              </div>
            </div>
          </SideCard>

          <SideCard title="支持功能">
            <ul className="space-y-5 text-[16px] text-[#172033]">
              {item.support_features.map((feature) => (
                <li key={feature} className="flex items-center gap-3">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#315efb]" />
                  {feature}
                </li>
              ))}
            </ul>
          </SideCard>

          <SideCard tint="blue" title="API 接入指南">
            <p className="text-[16px] leading-8 text-[#4d596a]">
              查看详细的API文档，了解如何快速集成此模型到您的应用中。
            </p>
            <button
              className="mt-8 flex h-[52px] w-full items-center justify-center rounded-[16px] bg-[#315efb] text-[18px] font-semibold text-white"
              onClick={scrollToExamples}
              type="button"
            >
              查看文档
            </button>
          </SideCard>
        </aside>
      </div>
    </section>
  );
}
