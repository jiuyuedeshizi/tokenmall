"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { apiFetch, setToken } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const result = await apiFetch<{ access_token: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ name, phone, email, password }),
      });
      setToken(result.access_token);
      router.replace("/overview");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "注册失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f5f8ff] px-6 py-10 text-[#172033]">
      <div className="mx-auto grid min-h-[calc(100vh-80px)] max-w-[1320px] overflow-hidden rounded-[36px] border border-[#e4ebf5] bg-white shadow-[0_24px_60px_rgba(33,80,163,0.08)] lg:grid-cols-[0.95fr_1.05fr]">
        <div className="hidden bg-[radial-gradient(circle_at_top_left,#dce8ff_0%,#edf3ff_38%,#ffffff_74%)] p-12 lg:flex lg:flex-col lg:justify-between">
          <Image alt="EAGET" className="h-auto w-[180px]" height={45} priority src="/logo.jpg" width={180} />
          <div className="max-w-[360px]">
            <div className="text-[44px] font-black leading-[1.05] tracking-[-0.05em]">Create your AI commerce workspace.</div>
            <p className="mt-6 text-[17px] leading-8 text-[#5d6b82]">
              注册后即可完成充值、模型管理、API 密钥创建和使用监控，快速搭建你的大模型开放平台。
            </p>
          </div>
        </div>

        <div className="flex items-center justify-center px-8 py-12 lg:px-14">
          <form className="w-full max-w-[560px]" onSubmit={handleSubmit}>
            <div className="mb-10">
              <h1 className="text-[40px] font-black tracking-[-0.04em]">创建账号</h1>
              <p className="mt-3 text-[17px] text-[#5d6b82]">完成基础信息后即可进入控制台，邮箱激活可在个人中心里完成。</p>
            </div>

            <div className="space-y-5">
              <AuthInput label="昵称" onChange={setName} placeholder="请输入昵称" value={name} />
              <AuthInput label="手机号" onChange={setPhone} placeholder="请输入手机号" value={phone} />
              <AuthInput label="邮箱" onChange={setEmail} placeholder="请输入邮箱" value={email} />
              <AuthInput label="密码" onChange={setPassword} placeholder="请设置登录密码" type="password" value={password} />
            </div>

            {error ? <p className="mt-5 text-[14px] text-[#ef4444]">{error}</p> : null}

            <button
              className="mt-8 h-[62px] w-full rounded-[20px] bg-[#172033] text-[20px] font-semibold text-white transition hover:opacity-92 disabled:opacity-60"
              disabled={submitting}
              type="submit"
            >
              {submitting ? "注册中..." : "注册并进入控制台"}
            </button>

            <div className="mt-6 text-[16px] text-[#5d6b82]">
              已有账号？{" "}
              <Link className="font-semibold text-[#315efb]" href="/login">
                返回登录
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function AuthInput({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-3 block text-[16px] font-semibold text-[#4d596a]">{label}</span>
      <input
        className="h-[60px] w-full rounded-[18px] border border-[#dbe3ef] px-5 text-[18px] outline-none transition placeholder:text-[#b6c0d0] focus:border-[#315efb]"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={type}
        value={value}
      />
    </label>
  );
}
