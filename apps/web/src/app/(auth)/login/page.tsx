"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { apiFetch, setToken } from "@/lib/api";

type LoginTab = "password" | "phone";

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState<LoginTab>("password");
  const [identifier, setIdentifier] = useState("admin@tokenmall.dev");
  const [password, setPassword] = useState("Admin123456");
  const [phone, setPhone] = useState("13800000000");
  const [code, setCode] = useState("");
  const [agreed, setAgreed] = useState(true);
  const [demoCode, setDemoCode] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);

  async function handlePasswordLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agreed) {
      setError("请先阅读并同意用户协议与隐私政策");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ identifier, password }),
      });
      setToken(result.access_token);
      router.replace("/overview");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSendCode() {
    if (!phone.trim()) {
      setError("请输入手机号");
      return;
    }
    setSendingCode(true);
    setError("");
    try {
      const result = await apiFetch<{ demo_code?: string }>("/auth/send-phone-code", {
        method: "POST",
        body: JSON.stringify({ phone }),
      });
      setDemoCode(result.demo_code ?? "");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "验证码发送失败");
    } finally {
      setSendingCode(false);
    }
  }

  async function handlePhoneLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agreed) {
      setError("请先阅读并同意用户协议与隐私政策");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await apiFetch<{ access_token: string }>("/auth/login-phone", {
        method: "POST",
        body: JSON.stringify({ phone, code }),
      });
      setToken(result.access_token);
      router.replace("/overview");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f6f8fc] text-[#172033]">
      <div className="grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative hidden overflow-hidden border-r border-[#e8edf5] bg-[linear-gradient(180deg,#fbfdff_0%,#f4f8ff_100%)] lg:block">
          <div className="absolute inset-y-0 right-0 w-px bg-[#e6edf8]" />
          <div className="absolute right-0 top-0 h-[240px] w-[360px] border-l-[3px] border-b-[3px] border-[#4f87ef] [clip-path:polygon(42%_0,100%_0,100%_100%,0_56%,0_0)]" />
          <div className="absolute right-0 top-0 h-[330px] w-[380px] bg-[linear-gradient(145deg,#ff972f_0%,#ff972f_45%,#5489f1_45%,#5489f1_100%)] [clip-path:polygon(54%_0,100%_0,100%_100%,20%_59%,20%_0)]" />
          <div className="absolute -bottom-9 -left-14 h-[215px] w-[215px] rounded-[74px] border-[3px] border-[#5d93f5] bg-[#d7e5ff]" />
          <div className="absolute bottom-[90px] left-[-24px] h-[228px] w-[228px] rounded-[74px] border-[3px] border-[#5d93f5]" />

          <div className="relative flex h-full flex-col px-[11%] py-[8%]">
            <Image alt="EAGET" className="h-auto w-[208px]" height={50} priority src="/eaget-logo.svg" width={208} />

            <div className="mt-auto pb-[12%]">
              <div className="max-w-[370px] text-[62px] font-black leading-[0.95] tracking-[-0.06em] text-[#101828]">
                <div>Intelligence</div>
                <div className="mt-1">with every</div>
                <div className="mt-1">
                  customer
                  <span className="ml-3 inline-block h-7 w-7 rounded-full bg-[#ff9a2f] align-middle" />
                </div>
              </div>

              <p className="mt-8 max-w-[430px] text-[17px] leading-8 text-[#65758d]">
                管理模型、密钥、计费、充值与后台运营，统一构建你的 AI 开放平台业务能力。
              </p>

              <div className="mt-8 flex max-w-[430px] flex-wrap gap-x-5 gap-y-2 text-[14px] font-medium text-[#738198]">
                <span>模型管理</span>
                <span>API 密钥</span>
                <span>余额计费</span>
                <span>运营后台</span>
              </div>
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center bg-white px-6 py-10 lg:px-12">
          <div className="w-full max-w-[520px]">
            <div className="mb-12 flex items-center gap-5">
              <Image alt="EAGET" className="h-auto w-[168px]" height={40} priority src="/eaget-logo.svg" width={168} />
              <div className="h-8 w-px bg-[#dde4ef]" />
              <div className="text-[17px] font-semibold text-[#172033]">开放平台账户登录</div>
            </div>

            <div className="mb-8 flex gap-10 border-b border-[#eef2f7] text-[17px] font-medium">
              {[
                { key: "password", label: "密码登录" },
                { key: "phone", label: "手机验证码登录" },
              ].map((item) => {
                const active = tab === item.key;
                return (
                  <button
                    key={item.key}
                    className={`relative pb-4 transition ${
                      active ? "text-[#315efb]" : "text-[#5b6678] hover:text-[#172033]"
                    }`}
                    onClick={() => {
                      setTab(item.key as LoginTab);
                      setError("");
                    }}
                    type="button"
                  >
                    {item.label}
                    <span className={`absolute bottom-[-1px] left-0 h-[2px] bg-[#315efb] transition-all ${active ? "w-full" : "w-0"}`} />
                  </button>
                );
              })}
            </div>

            {tab === "password" ? (
              <form className="space-y-6" onSubmit={handlePasswordLogin}>
                <input
                  className="h-[64px] w-full rounded-[16px] border border-[#e4e9f2] bg-[#f7f9fc] px-7 text-[18px] text-[#172033] outline-none transition placeholder:text-[#b7c1cf] focus:border-[#c9d8f9] focus:bg-white focus:shadow-[0_0_0_4px_rgba(49,94,251,0.05)]"
                  onChange={(event) => setIdentifier(event.target.value)}
                  placeholder="请输入手机号/邮箱"
                  value={identifier}
                />
                <input
                  className="h-[64px] w-full rounded-[16px] border border-[#e4e9f2] bg-[#f7f9fc] px-7 text-[18px] text-[#172033] outline-none transition placeholder:text-[#b7c1cf] focus:border-[#c9d8f9] focus:bg-white focus:shadow-[0_0_0_4px_rgba(49,94,251,0.05)]"
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="请输入登录密码"
                  type="password"
                  value={password}
                />
                <PolicyCheckbox agreed={agreed} setAgreed={setAgreed} />
                {error ? <p className="text-[14px] text-[#ef4444]">{error}</p> : null}
                <button
                  className="h-[62px] w-full rounded-[18px] bg-[#182136] text-[21px] font-semibold text-white transition hover:opacity-95 disabled:opacity-60"
                  disabled={submitting}
                  type="submit"
                >
                  {submitting ? "登录中..." : "立即登录"}
                </button>
                <div className="flex items-center justify-between text-[15px] text-[#172033]">
                  <span className="cursor-pointer hover:text-[#315efb]">忘记密码</span>
                  <div className="flex items-center gap-6">
                    <span>邮箱验证码登录</span>
                    <span>子账号登录</span>
                  </div>
                </div>
              </form>
            ) : (
              <form className="space-y-6" onSubmit={handlePhoneLogin}>
                <input
                  className="h-[64px] w-full rounded-[16px] border border-[#e4e9f2] bg-[#f7f9fc] px-7 text-[18px] text-[#172033] outline-none transition placeholder:text-[#b7c1cf] focus:border-[#c9d8f9] focus:bg-white focus:shadow-[0_0_0_4px_rgba(49,94,251,0.05)]"
                  onChange={(event) => setPhone(event.target.value)}
                  placeholder="请输入手机号"
                  value={phone}
                />
                <div className="grid grid-cols-[1fr_auto] gap-4">
                  <input
                    className="h-[64px] rounded-[16px] border border-[#e4e9f2] bg-[#f7f9fc] px-7 text-[18px] text-[#172033] outline-none transition placeholder:text-[#b7c1cf] focus:border-[#c9d8f9] focus:bg-white focus:shadow-[0_0_0_4px_rgba(49,94,251,0.05)]"
                    onChange={(event) => setCode(event.target.value)}
                    placeholder="请输入短信验证码"
                    value={code}
                  />
                  <button
                    className="h-[64px] rounded-[16px] border border-[#dbe3ef] px-6 text-[16px] font-semibold text-[#315efb] transition hover:bg-[#f4f8ff] disabled:opacity-60"
                    disabled={sendingCode}
                    onClick={handleSendCode}
                    type="button"
                  >
                    {sendingCode ? "发送中..." : "获取验证码"}
                  </button>
                </div>
                {demoCode ? <p className="text-[14px] text-[#315efb]">演示验证码：{demoCode}</p> : null}
                <PolicyCheckbox agreed={agreed} setAgreed={setAgreed} />
                {error ? <p className="text-[14px] text-[#ef4444]">{error}</p> : null}
                <button
                  className="h-[62px] w-full rounded-[18px] bg-[#182136] text-[21px] font-semibold text-white transition hover:opacity-95 disabled:opacity-60"
                  disabled={submitting}
                  type="submit"
                >
                  {submitting ? "登录中..." : "立即登录"}
                </button>
              </form>
            )}

            <div className="mt-8 text-[16px] text-[#5d6b82]">
              还没有账号？{" "}
              <Link className="font-semibold text-[#315efb]" href="/register">
                立即注册
              </Link>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function PolicyCheckbox({
  agreed,
  setAgreed,
}: {
  agreed: boolean;
  setAgreed: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-3 text-[15px] text-[#5d6b82]">
      <input
        checked={agreed}
        className="h-4 w-4 rounded border-[#d9e1ef] text-[#315efb]"
        onChange={(event) => setAgreed(event.target.checked)}
        type="checkbox"
      />
      我已经仔细查看并同意该
      <span className="text-[#315efb]">用户协议</span>
      与
      <span className="text-[#315efb]">隐私政策</span>
    </label>
  );
}
