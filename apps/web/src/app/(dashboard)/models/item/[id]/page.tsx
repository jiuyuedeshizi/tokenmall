"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { apiFetch } from "@/lib/api";
import type { ModelInfo, PricingItem } from "@/types";

function formatPrice(value: string) {
  if (!value || Number.isNaN(Number(value))) {
    return value;
  }
  return Number(value).toLocaleString("zh-CN", {
    maximumFractionDigits: 2,
  });
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

function pricingCardTint(index: number) {
  return index % 2 === 0
    ? { bg: "bg-[#eef4ff]", text: "text-[#315efb]" }
    : { bg: "bg-[#edf9f0]", text: "text-[#16a34a]" };
}

function renderPricingSummary(items: PricingItem[]) {
  if (!items.length) {
    return [{ label: "价格待补充", unit: "", price: "-" }];
  }
  return items;
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

function isBailianNativeImageModel(item: ModelInfo) {
  return (
    item.provider === "alibaba-bailian" &&
    item.capability_type === "image" &&
    (item.model_id === "qwen-image-2.0" || item.model_id === "qwen-image-2.0-pro")
  );
}

function isChatCompatibleAsrModel(item: ModelInfo) {
  return item.provider === "alibaba-bailian" && item.model_id === "qwen3-asr-flash";
}

function isBailianNativeTtsModel(item: ModelInfo) {
  return item.provider === "alibaba-bailian" && item.model_id === "qwen3-tts-vd-2026-01-26";
}

function isBailianVideoModel(item: ModelInfo) {
  return item.provider === "alibaba-bailian" && item.model_id === "wan2.6-i2v-flash";
}

function buildDefaultPythonSnippet(item: ModelInfo, baseUrl: string) {
  if (isBailianNativeImageModel(item)) {
    return [
      "import requests",
      "",
      `url = "${baseUrl}/api/v1/services/aigc/multimodal-generation/generation"`,
      "headers = {",
      '    "Authorization": "Bearer YOUR_API_KEY",',
      '    "Content-Type": "application/json"',
      "}",
      "data = {",
      `    "model": "${item.model_id}",`,
      '    "input": {',
      '        "messages": [',
      "            {",
      '                "role": "user",',
      '                "content": [',
      "                    {",
      '                        "text": "一只戴围巾的橘猫，写实风格，干净背景。"',
      "                    }",
      "                ]",
      "            }",
      "        ]",
      "    },",
      '    "parameters": {',
      '        "watermark": False,',
      '        "size": "1024*1024"',
      "    }",
      "}",
      "",
      "response = requests.post(url, headers=headers, json=data)",
      "print(response.json())",
    ].join("\n");
  }

  if (isChatCompatibleAsrModel(item)) {
    return [
      "import requests",
      "",
      `url = "${baseUrl}/v1/chat/completions"`,
      "headers = {",
      '    "Authorization": "Bearer YOUR_API_KEY",',
      '    "Content-Type": "application/json"',
      "}",
      "data = {",
      `    "model": "${item.model_id}",`,
      '    "messages": [',
      "        {",
      '            "role": "user",',
      '            "content": [',
      "                {",
      '                    "type": "input_audio",',
      '                    "input_audio": {',
      '                        "data": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"',
      "                    }",
      "                }",
      "            ]",
      "        }",
      "    ],",
      '    "stream": False,',
      '    "asr_options": {',
      '        "enable_itn": False',
      "    }",
      "}",
      "",
      "response = requests.post(url, headers=headers, json=data)",
      "print(response.json())",
    ].join("\n");
  }

  if (isBailianNativeTtsModel(item)) {
    return [
      "import requests",
      "",
      `customize_url = "${baseUrl}/api/v1/services/audio/tts/customization"`,
      `tts_url = "${baseUrl}/api/v1/services/aigc/multimodal-generation/generation"`,
      "",
      "# 第一步：创建或查询声音设计音色，target_model 必须和后续合成模型一致",
      "customize_payload = {",
      '    "model": "qwen-voice-design",',
      '    "input": {',
      '        "action": "list",',
      '        "page_size": 10,',
      '        "page_index": 0',
      "    }",
      "}",
      "headers = {",
      '    "Authorization": "Bearer YOUR_API_KEY",',
      '    "Content-Type": "application/json"',
      "}",
      "customize_response = requests.post(customize_url, headers=headers, json=customize_payload, timeout=120)",
      "customize_response.raise_for_status()",
      "voices = customize_response.json()",
      "# 这里请替换成你通过声音设计接口创建出来的专属音色名",
      'voice_name = "yourVoice"',
      "",
      "# 第二步：使用专属音色进行语音合成",
      "tts_payload = {",
      `    "model": "${item.model_id}",`,
      '    "input": {',
      '        "text": "那我来给大家推荐一款 T 恤，这款呢真的是超级好看。",',
      '        "voice": voice_name,',
      '        "language_type": "Chinese"',
      "    }",
      "}",
      "response = requests.post(tts_url, headers=headers, json=tts_payload, timeout=120)",
      "print(response.json())",
      "",
      "# 流式：增加 X-DashScope-SSE 请求头，逐段消费 SSE 事件",
      "stream_headers = {**headers, 'X-DashScope-SSE': 'enable'}",
      "with requests.post(tts_url, headers=stream_headers, json=tts_payload, stream=True, timeout=120) as stream_resp:",
      "    for line in stream_resp.iter_lines(decode_unicode=True):",
      "        if line:",
      "            print(line)",
    ].join("\n");
  }

  if (isBailianVideoModel(item)) {
    return [
      "import requests",
      "",
      `submit_url = "${baseUrl}/api/v1/services/aigc/video-generation/video-synthesis"`,
      `task_url = "${baseUrl}/api/v1/tasks/{task_id}"`,
      "headers = {",
      '    "Authorization": "Bearer YOUR_API_KEY",',
      '    "Content-Type": "application/json",',
      '    "X-DashScope-Async": "enable"',
      "}",
      "payload = {",
      `    "model": "${item.model_id}",`,
      '    "input": {',
      '        "prompt": "一只猫在草地上奔跑，镜头跟随，光线明亮自然。",',
      '        "img_url": "https://cdn.translate.alibaba.com/r/wanx-demo-1.png"',
      "    },",
      '    "parameters": {',
      '        "audio": false,',
      '        "resolution": "720P",',
      '        "prompt_extend": True,',
      '        "watermark": True,',
      '        "duration": 5',
      "    }",
      "}",
      "submit_resp = requests.post(submit_url, headers=headers, json=payload, timeout=120)",
      "submit_data = submit_resp.json()",
      "task_id = submit_data['output']['task_id']",
      "print(task_id)",
      "",
      "# 轮询任务结果",
      "status_headers = {k: v for k, v in headers.items() if k != 'X-DashScope-Async'}",
      "result_resp = requests.get(task_url.format(task_id=task_id), headers=status_headers, timeout=120)",
      "print(result_resp.json())",
    ].join("\n");
  }

  return [
    "import requests",
    "",
    `url = "${baseUrl}/v1/chat/completions"`,
    "headers = {",
    '    "Authorization": "Bearer YOUR_API_KEY",',
    '    "Content-Type": "application/json"',
    "}",
    "data = {",
    `    "model": "${item.model_id}",`,
    '    "messages": [{"role": "user", "content": "你好"}]',
    "}",
    "",
    "response = requests.post(url, headers=headers, json=data)",
    "print(response.json())",
  ].join("\n");
}

function buildDefaultTypescriptSnippet(item: ModelInfo, baseUrl: string) {
  if (isBailianNativeImageModel(item)) {
    return [
      `const response = await fetch('${baseUrl}/api/v1/services/aigc/multimodal-generation/generation', {`,
      "  method: 'POST',",
      "  headers: {",
      "    'Authorization': 'Bearer YOUR_API_KEY',",
      "    'Content-Type': 'application/json'",
      "  },",
      "  body: JSON.stringify({",
      `    model: '${item.model_id}',`,
      "    input: {",
      "      messages: [",
      "        {",
      "          role: 'user',",
      "          content: [{ text: '一只戴围巾的橘猫，写实风格，干净背景。' }]",
      "        }",
      "      ]",
      "    },",
      "    parameters: {",
      "      watermark: false,",
      "      size: '1024*1024'",
      "    }",
      "  })",
      "});",
      "",
      "const data = await response.json();",
      "console.log(data);",
    ].join("\n");
  }

  if (isChatCompatibleAsrModel(item)) {
    return [
      `const response = await fetch('${baseUrl}/v1/chat/completions', {`,
      "  method: 'POST',",
      "  headers: {",
      "    'Authorization': 'Bearer YOUR_API_KEY',",
      "    'Content-Type': 'application/json'",
      "  },",
      "  body: JSON.stringify({",
      `    model: '${item.model_id}',`,
      "    messages: [",
      "      {",
      "        role: 'user',",
      "        content: [",
      "          {",
      "            type: 'input_audio',",
      "            input_audio: {",
      "              data: 'https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3'",
      "            }",
      "          }",
      "        ]",
      "      }",
      "    ],",
      "    stream: false,",
      "    asr_options: {",
      "      enable_itn: false",
      "    }",
      "  })",
      "});",
      "",
      "const data = await response.json();",
      "console.log(data);",
    ].join("\n");
  }

  if (isBailianNativeTtsModel(item)) {
    return [
      `const customizeUrl = '${baseUrl}/api/v1/services/audio/tts/customization';`,
      `const ttsUrl = '${baseUrl}/api/v1/services/aigc/multimodal-generation/generation';`,
      "const headers = {",
      "  'Authorization': 'Bearer YOUR_API_KEY',",
      "  'Content-Type': 'application/json'",
      "};",
      "",
      "// 第一步：列出或创建声音设计音色",
      "const customizeResponse = await fetch(customizeUrl, {",
      "  method: 'POST',",
      "  headers,",
      "  body: JSON.stringify({",
      "    model: 'qwen-voice-design',",
      "    input: {",
      "      action: 'list',",
      "      page_size: 10,",
      "      page_index: 0",
      "    }",
      "  })",
      "});",
      "const voices = await customizeResponse.json();",
      "// 请替换成你通过声音设计接口创建出来的专属音色名",
      "const voiceName = 'yourVoice';",
      "",
      "// 第二步：使用专属音色进行语音合成",
      "const payload = {",
      `  model: '${item.model_id}',`,
      "  input: {",
      "    text: '那我来给大家推荐一款 T 恤，这款呢真的是超级好看。',",
      "    voice: voiceName,",
      "    language_type: 'Chinese'",
      "  }",
      "};",
      "",
      "// 非流式",
      "const response = await fetch(ttsUrl, {",
      "  method: 'POST',",
      "  headers,",
      "  body: JSON.stringify(payload)",
      "});",
      "const data = await response.json();",
      "console.log(data);",
      "",
      "// 流式 SSE",
      "const streamResponse = await fetch(ttsUrl, {",
      "  method: 'POST',",
      "  headers: {",
      "    ...headers,",
      "    'X-DashScope-SSE': 'enable'",
      "  },",
      "  body: JSON.stringify(payload)",
      "});",
      "const reader = streamResponse.body?.getReader();",
      "const decoder = new TextDecoder();",
      "while (reader) {",
      "  const { value, done } = await reader.read();",
      "  if (done) break;",
      "  console.log(decoder.decode(value, { stream: true }));",
      "}",
    ].join("\n");
  }

  if (isBailianVideoModel(item)) {
    return [
      `const submitUrl = '${baseUrl}/api/v1/services/aigc/video-generation/video-synthesis';`,
      "const payload = {",
      `  model: '${item.model_id}',`,
      "  input: {",
      "    prompt: '一只猫在草地上奔跑，镜头跟随，光线明亮自然。',",
      "    img_url: 'https://cdn.translate.alibaba.com/r/wanx-demo-1.png'",
      "  },",
      "  parameters: {",
      "    audio: false,",
      "    resolution: '720P',",
      "    prompt_extend: true,",
      "    watermark: true,",
      "    duration: 5",
      "  }",
      "};",
      "",
      "const submitResponse = await fetch(submitUrl, {",
      "  method: 'POST',",
      "  headers: {",
      "    'Authorization': 'Bearer YOUR_API_KEY',",
      "    'Content-Type': 'application/json',",
      "    'X-DashScope-Async': 'enable'",
      "  },",
      "  body: JSON.stringify(payload)",
      "});",
      "const submitData = await submitResponse.json();",
      "const taskId = submitData.output.task_id;",
      "",
      "const resultResponse = await fetch(`${submitUrl.replace('/services/aigc/video-generation/video-synthesis', '')}/tasks/${taskId}`, {",
      "  headers: {",
      "    'Authorization': 'Bearer YOUR_API_KEY'",
      "  }",
      "});",
      "const resultData = await resultResponse.json();",
      "console.log(resultData);",
    ].join("\n");
  }

  return [
    `const response = await fetch('${baseUrl}/v1/chat/completions', {`,
    "  method: 'POST',",
    "  headers: {",
    "    'Authorization': 'Bearer YOUR_API_KEY',",
    "    'Content-Type': 'application/json'",
    "  },",
    "  body: JSON.stringify({",
    `    model: '${item.model_id}',`,
    "    messages: [{ role: 'user', content: '你好' }]",
    "  })",
    "});",
    "",
    "const data = await response.json();",
    "console.log(data);",
  ].join("\n");
}

function buildDefaultCurlSnippet(item: ModelInfo, baseUrl: string) {
  if (isBailianNativeImageModel(item)) {
    return [
      `curl -X POST ${baseUrl}/api/v1/services/aigc/multimodal-generation/generation \\`,
      '  -H "Authorization: Bearer YOUR_API_KEY" \\',
      '  -H "Content-Type: application/json" \\',
      "  -d '{",
      `    "model": "${item.model_id}",`,
      '    "input": {',
      '      "messages": [',
      "        {",
      '          "role": "user",',
      '          "content": [',
      "            {",
      '              "text": "一只戴围巾的橘猫，写实风格，干净背景。"',
      "            }",
      "          ]",
      "        }",
      "      ]",
      "    },",
      '    "parameters": {',
      '      "watermark": false,',
      '      "size": "1024*1024"',
      "    }",
      "  }'",
    ].join("\n");
  }

  if (isChatCompatibleAsrModel(item)) {
    return [
      `curl -X POST ${baseUrl}/v1/chat/completions \\`,
      '  -H "Authorization: Bearer YOUR_API_KEY" \\',
      '  -H "Content-Type: application/json" \\',
      "  -d '{",
      `    "model": "${item.model_id}",`,
      '    "messages": [',
      "      {",
      '        "role": "user",',
      '        "content": [',
      "          {",
      '            "type": "input_audio",',
      '            "input_audio": {',
      '              "data": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"',
      "            }",
      "          }",
      "        ]",
      "      }",
      "    ],",
      '    "stream": false,',
      '    "asr_options": {',
      '      "enable_itn": false',
      "    }",
      "  }'",
    ].join("\n");
  }

  if (isBailianNativeTtsModel(item)) {
    return [
      `curl -X POST ${baseUrl}/api/v1/services/audio/tts/customization \\`,
      '  -H "Authorization: Bearer YOUR_API_KEY" \\',
      '  -H "Content-Type: application/json" \\',
      "  -d '{",
      '    "model": "qwen-voice-design",',
      '    "input": {',
      '      "action": "list",',
      '      "page_size": 10,',
      '      "page_index": 0',
      "    }",
      "  }'",
      "",
      "# 将第二步中的 yourVoice 替换为你通过声音设计接口创建出的专属音色名",
      `curl -X POST ${baseUrl}/api/v1/services/aigc/multimodal-generation/generation \\`,
      '  -H "Authorization: Bearer YOUR_API_KEY" \\',
      '  -H "Content-Type: application/json" \\',
      "  -d '{",
      `    "model": "${item.model_id}",`,
      '    "input": {',
      '      "text": "那我来给大家推荐一款 T 恤，这款呢真的是超级好看。",',
      '      "voice": "yourVoice",',
      '      "language_type": "Chinese"',
      "    }",
      "  }'",
      "",
      "# 流式 SSE",
      `curl -X POST ${baseUrl}/api/v1/services/aigc/multimodal-generation/generation \\`,
      '  -H "Authorization: Bearer YOUR_API_KEY" \\',
      '  -H "Content-Type: application/json" \\',
      '  -H "X-DashScope-SSE: enable" \\',
      "  -d '{",
      `    "model": "${item.model_id}",`,
      '    "input": {',
      '      "text": "那我来给大家推荐一款T恤，这款呢真的是超级好看。",',
      '      "voice": "myvoice",',
      '      "language_type": "Chinese"',
      "    }",
      "  }'",
    ].join("\n");
  }

  if (isBailianVideoModel(item)) {
    return [
      `curl -X POST ${baseUrl}/api/v1/services/aigc/video-generation/video-synthesis \\`,
      '  -H "Authorization: Bearer YOUR_API_KEY" \\',
      '  -H "Content-Type: application/json" \\',
      '  -H "X-DashScope-Async: enable" \\',
      "  -d '{",
      `    "model": "${item.model_id}",`,
      '    "input": {',
      '      "prompt": "一只猫在草地上奔跑，镜头跟随，光线明亮自然。",',
      '      "img_url": "https://cdn.translate.alibaba.com/r/wanx-demo-1.png"',
      "    },",
      '    "parameters": {',
      '      "audio": false,',
      '      "resolution": "720P",',
      '      "prompt_extend": true,',
      '      "watermark": true,',
      '      "duration": 5',
      "    }",
      "  }'",
      "",
      `curl -X GET ${baseUrl}/api/v1/tasks/{task_id} \\`,
      '  -H "Authorization: Bearer YOUR_API_KEY"',
    ].join("\n");
  }

  return [
    `curl -X POST ${baseUrl}/v1/chat/completions \\`,
    '  -H "Authorization: Bearer YOUR_API_KEY" \\',
    '  -H "Content-Type: application/json" \\',
    "  -d '{",
    `    "model": "${item.model_id}",`,
    '    "messages": [{"role": "user", "content": "你好"}]',
    "  }'",
  ].join("\n");
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

const CODE_THEMES = {
  ocean: {
    label: "海蓝",
    frame: "border-[#d8e7ff] bg-[linear-gradient(180deg,#f8fbff_0%,#eef5ff_100%)]",
    toolbar: "border-[#dbe8ff] bg-white/78",
    code: "bg-[#0f172a] text-[#e6eefc]",
    gutter: "text-[#6b7ea8]",
    plain: "text-[#dbe7ff]",
    keyword: "text-[#7dd3fc]",
    string: "text-[#f9c97e]",
    comment: "text-[#7c8da8]",
    number: "text-[#86efac]",
    accent: "bg-[#315efb] text-white",
    pill: "bg-[#e8f0ff] text-[#315efb]",
    idle: "bg-white text-[#5f6f8d]",
  },
  sand: {
    label: "暖砂",
    frame: "border-[#eadcc5] bg-[linear-gradient(180deg,#fffdf8_0%,#f9f2e6_100%)]",
    toolbar: "border-[#ebdfcc] bg-white/76",
    code: "bg-[#2a2119] text-[#f8efe1]",
    gutter: "text-[#a78a6e]",
    plain: "text-[#f3eadc]",
    keyword: "text-[#fcae6b]",
    string: "text-[#f8d66d]",
    comment: "text-[#9f8d78]",
    number: "text-[#9ae6b4]",
    accent: "bg-[#a65a2e] text-white",
    pill: "bg-[#f8ead6] text-[#a65a2e]",
    idle: "bg-white text-[#7f6a57]",
  },
  slate: {
    label: "石墨",
    frame: "border-[#d9dee7] bg-[linear-gradient(180deg,#fbfcfe_0%,#f2f5fa_100%)]",
    toolbar: "border-[#e1e6ef] bg-white/80",
    code: "bg-[#111827] text-[#e5e7eb]",
    gutter: "text-[#76839b]",
    plain: "text-[#dde3ee]",
    keyword: "text-[#93c5fd]",
    string: "text-[#fcd34d]",
    comment: "text-[#7b8798]",
    number: "text-[#c4f1be]",
    accent: "bg-[#172033] text-white",
    pill: "bg-[#ecf0f6] text-[#172033]",
    idle: "bg-white text-[#667085]",
  },
} as const;

type CodeTheme = keyof typeof CODE_THEMES;

function tokenizeCodeLine(line: string) {
  const tokens: Array<{ value: string; type: "plain" | "keyword" | "string" | "comment" | "number" }> = [];
  const pattern =
    /(#[^\n]*$|\/\/.*$|"(?:\\.|[^"])*"|'(?:\\.|[^'])*'|\b(?:const|let|var|await|async|return|import|from|with|for|while|break|continue|if|else|elif|def|class|try|except|finally|raise|print|true|false|null|None|True|False)\b|\b\d+(?:\.\d+)?\b)/g;
  let lastIndex = 0;

  for (const match of line.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      tokens.push({ value: line.slice(lastIndex, index), type: "plain" });
    }
    const value = match[0];
    let type: "plain" | "keyword" | "string" | "comment" | "number" = "plain";
    if (value.startsWith("#") || value.startsWith("//")) {
      type = "comment";
    } else if (value.startsWith('"') || value.startsWith("'")) {
      type = "string";
    } else if (/^\d/.test(value)) {
      type = "number";
    } else {
      type = "keyword";
    }
    tokens.push({ value, type });
    lastIndex = index + value.length;
  }

  if (lastIndex < line.length) {
    tokens.push({ value: line.slice(lastIndex), type: "plain" });
  }

  return tokens.length ? tokens : [{ value: line, type: "plain" as const }];
}

function CodeExampleViewer({
  modelId,
  snippets,
  onCopy,
}: {
  modelId: string;
  snippets: Array<{ language: string; code: string }>;
  onCopy: (value: string) => void;
}) {
  const [activeLanguage, setActiveLanguage] = useState(snippets[0]?.language ?? "Python");
  const [theme, setTheme] = useState<CodeTheme>("ocean");

  useEffect(() => {
    if (!snippets.some((snippet) => snippet.language === activeLanguage)) {
      setActiveLanguage(snippets[0]?.language ?? "Python");
    }
  }, [activeLanguage, snippets]);

  const activeSnippet = snippets.find((snippet) => snippet.language === activeLanguage) ?? snippets[0];
  const themeConfig = CODE_THEMES[theme];
  const highlightedLines = useMemo(
    () => (activeSnippet?.code ?? "").split("\n").map((line) => tokenizeCodeLine(line)),
    [activeSnippet],
  );

  if (!activeSnippet) {
    return null;
  }

  return (
    <div className={`mt-6 rounded-[24px] border p-4 ${themeConfig.frame}`}>
      <div className={`rounded-[18px] border px-4 py-3 ${themeConfig.toolbar}`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`rounded-full px-3 py-1 text-[12px] font-semibold ${themeConfig.pill}`}>
              API 示例
            </span>
            <div className="flex flex-wrap gap-2">
              {snippets.map((snippet) => (
                <button
                  key={snippet.language}
                  className={`rounded-full px-4 py-2 text-[13px] font-semibold transition ${
                    snippet.language === activeLanguage ? themeConfig.accent : themeConfig.idle
                  }`}
                  onClick={() => setActiveLanguage(snippet.language)}
                  type="button"
                >
                  {snippet.language}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {Object.entries(CODE_THEMES).map(([themeKey, value]) => (
              <button
                key={themeKey}
                className={`rounded-full px-3 py-1.5 text-[12px] font-semibold transition ${
                  theme === themeKey ? themeConfig.accent : themeConfig.idle
                }`}
                onClick={() => setTheme(themeKey as CodeTheme)}
                type="button"
              >
                {value.label}
              </button>
            ))}
            <button
              className="ml-2 flex items-center gap-2 rounded-full bg-white px-4 py-2 text-[13px] font-semibold text-[#315efb] shadow-sm"
              onClick={() => onCopy(activeSnippet.code)}
              type="button"
            >
              <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 24 24">
                <rect height="14" rx="2" stroke="currentColor" strokeWidth="2" width="14" x="8" y="6" />
                <path
                  d="M16 4H6a2 2 0 0 0-2 2v10"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                />
              </svg>
              复制代码
            </button>
          </div>
        </div>
      </div>
      <div className={`mt-4 overflow-hidden rounded-[20px] ${themeConfig.code}`}>
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-3 text-[12px] uppercase tracking-[0.24em] text-white/70">
          <span>{activeSnippet.language}</span>
          <span>{modelId}</span>
        </div>
        <div className="overflow-x-auto px-0 py-4">
          <code className="block min-w-full font-mono text-[13px] leading-7">
            {highlightedLines.map((line, index) => (
              <div key={index} className="grid grid-cols-[56px_minmax(0,1fr)] px-5">
                <span className={`select-none pr-4 text-right ${themeConfig.gutter}`}>{index + 1}</span>
                <span className="whitespace-pre">
                  {line.map((token, tokenIndex) => (
                    <span
                      key={`${index}-${tokenIndex}`}
                      className={
                        token.type === "keyword"
                          ? themeConfig.keyword
                          : token.type === "string"
                            ? themeConfig.string
                            : token.type === "comment"
                              ? themeConfig.comment
                              : token.type === "number"
                                ? themeConfig.number
                                : themeConfig.plain
                      }
                    >
                      {token.value || " "}
                    </span>
                  ))}
                </span>
              </div>
            ))}
          </code>
        </div>
      </div>
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
    const python = item.example_python || buildDefaultPythonSnippet(item, baseUrl);
    const typescript = item.example_typescript || buildDefaultTypescriptSnippet(item, baseUrl);
    const curl = item.example_curl || buildDefaultCurlSnippet(item, baseUrl);

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
            <div className="mt-3 text-[15px] text-[#667085]">{formatBillingMode(item.billing_mode)}</div>
            <div className="mt-7 grid gap-5 md:grid-cols-2">
              {renderPricingSummary(item.pricing_items).map((pricingItem, index) => (
                <div key={`${pricingItem.label}-${index}`} className={`rounded-[18px] p-6 ${pricingCardTint(index).bg}`}>
                  <div className="text-[16px] text-[#4d596a]">{pricingItem.label}</div>
                  <div className={`mt-4 text-[28px] font-semibold ${pricingCardTint(index).text}`}>
                    ¥{formatPrice(pricingItem.price)}/{pricingItem.unit}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section
            className="rounded-[22px] border border-[#e5eaf3] bg-white p-8"
            id="api-examples"
          >
            <h2 className="text-[22px] font-semibold text-[#172033]">API 使用示例</h2>
            <p className="mt-3 text-[15px] leading-7 text-[#667085]">
              示例内容优先读取后台配置；如果后台没有单独设置，页面会自动回退到系统默认示例。
            </p>
            <CodeExampleViewer
              modelId={item.model_id}
              snippets={snippets}
              onCopy={(value) => void copyText(value)}
            />
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
              {item.supports_multimodal_chat ? (
                <div>
                  <div className="text-[#667085]">多模态 Chat</div>
                  <div className="mt-2">
                    <span className="rounded-full bg-[#e8f7ee] px-3 py-1 text-[13px] font-semibold text-[#0f9f57]">
                      已验证支持多模态输入
                    </span>
                  </div>
                </div>
              ) : null}
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
              {isBailianNativeImageModel(item)
                ? "该模型使用阿里百炼原生图像生成接口，不走 /v1/chat/completions。请按下方原生接口示例接入。"
                : isBailianVideoModel(item)
                  ? "该模型使用阿里百炼异步视频生成接口。先提交 video-synthesis 任务拿 task_id，再轮询 /api/v1/tasks/{task_id} 获取视频地址。"
                : isBailianNativeTtsModel(item)
                  ? "该模型使用阿里百炼原生多模态生成接口，支持普通 JSON 返回与 X-DashScope-SSE 流式返回；voice 请替换为声音设计生成的专属音色。"
                : isChatCompatibleAsrModel(item)
                  ? "该模型使用 /v1/chat/completions 兼容接口，并通过 input_audio 传入音频内容。"
                : "查看详细的API文档，了解如何快速集成此模型到您的应用中。"}
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
