"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { apiFetch, setToken } from "@/lib/api";

type LoginTab = "password" | "phone" | "email";
const LOGIN_TABS: Array<{ key: LoginTab; label: string }> = [
  { key: "password", label: "密码登录" },
  { key: "phone", label: "手机验证码登录" },
  { key: "email", label: "邮箱验证码登录" },
];

type CodeSendResult = {
  demo_code?: string;
  message?: string;
  cooldown_seconds?: number;
};

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState<LoginTab>("password");
  const [identifier, setIdentifier] = useState("admin@tokenmall.dev");
  const [password, setPassword] = useState("Admin123456");
  const [phone, setPhone] = useState("13800000000");
  const [phoneCode, setPhoneCode] = useState("");
  const [email, setEmail] = useState("admin@tokenmall.dev");
  const [emailCode, setEmailCode] = useState("");
  const [agreed, setAgreed] = useState(true);
  const [phoneDemoCode, setPhoneDemoCode] = useState("");
  const [emailDemoCode, setEmailDemoCode] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sendingPhoneCode, setSendingPhoneCode] = useState(false);
  const [sendingEmailCode, setSendingEmailCode] = useState(false);
  const [phoneCooldown, setPhoneCooldown] = useState(0);
  const [emailCooldown, setEmailCooldown] = useState(0);

  useEffect(() => {
    if (phoneCooldown <= 0 && emailCooldown <= 0) {
      return;
    }

    const timer = window.setInterval(() => {
      setPhoneCooldown((value) => (value > 0 ? value - 1 : 0));
      setEmailCooldown((value) => (value > 0 ? value - 1 : 0));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [phoneCooldown, emailCooldown]);

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
    setSendingPhoneCode(true);
    setError("");
    setNotice("");
    try {
      const result = await apiFetch<CodeSendResult>("/auth/send-phone-code", {
        method: "POST",
        body: JSON.stringify({ phone }),
      });
      setPhoneDemoCode(result.demo_code ?? "");
      setPhoneCooldown(result.cooldown_seconds ?? 60);
      setNotice(result.message ?? "验证码已发送，请查收");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "验证码发送失败");
    } finally {
      setSendingPhoneCode(false);
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
        body: JSON.stringify({ phone, code: phoneCode }),
      });
      setToken(result.access_token);
      router.replace("/overview");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSendEmailCode() {
    if (!email.trim()) {
      setError("请输入邮箱");
      return;
    }
    setSendingEmailCode(true);
    setError("");
    setNotice("");
    try {
      const result = await apiFetch<CodeSendResult>("/auth/send-email-code", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setEmailDemoCode(result.demo_code ?? "");
      setEmailCooldown(result.cooldown_seconds ?? 60);
      setNotice(result.message ?? "验证码已发送，请查收");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "验证码发送失败");
    } finally {
      setSendingEmailCode(false);
    }
  }

  async function handleEmailLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agreed) {
      setError("请先阅读并同意用户协议与隐私政策");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await apiFetch<{ access_token: string }>("/auth/login-email", {
        method: "POST",
        body: JSON.stringify({ email, code: emailCode }),
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
        <section className="relative hidden min-h-screen overflow-hidden border-r border-[#e8edf5] bg-[#dcecff] lg:block">
          <Image alt="忆捷EAGET 登录页视觉" className="object-cover object-center" fill priority sizes="50vw" src="/login-hero.png" />
        </section>

        <section className="flex items-center justify-center bg-white px-6 py-10 lg:px-12">
          <div className="w-full max-w-[560px]">
            <div className="mb-12 flex items-center gap-5">
              <div className="text-[42px] font-black italic leading-none tracking-[-0.05em] text-[#127DCA]">
                {/* <span className="mr-1 not-italic tracking-[-0.04em]">忆捷EAGET</span> */}
                <span>忆捷EAGET</span>
              </div>
              <div className="h-8 w-px bg-[#dde4ef]" />
              <div className="text-[17px] font-semibold text-[#172033]">开放平台账户登录</div>
            </div>

            <div className="mb-8 flex gap-10 border-b border-[#eef2f7] text-[17px] font-medium">
              {LOGIN_TABS.map((item) => {
                const active = tab === item.key;
                return (
                  <button
                    key={item.key}
                    className={`relative pb-4 transition ${
                      active ? "text-[#315efb]" : "text-[#5b6678] hover:text-[#172033]"
                    }`}
                    onClick={() => {
                      setTab(item.key);
                      setError("");
                      setNotice("");
                      setPhoneDemoCode("");
                      setEmailDemoCode("");
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
                {notice ? <p className="text-[14px] text-[#315efb]">{notice}</p> : null}
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
                </div>
              </form>
            ) : tab === "phone" ? (
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
                    onChange={(event) => setPhoneCode(event.target.value)}
                    placeholder="请输入短信验证码"
                    value={phoneCode}
                  />
                  <button
                    className="h-[64px] rounded-[16px] border border-[#dbe3ef] px-6 text-[16px] font-semibold text-[#315efb] transition hover:bg-[#f4f8ff] disabled:opacity-60"
                    disabled={sendingPhoneCode || phoneCooldown > 0}
                    onClick={handleSendCode}
                    type="button"
                  >
                    {sendingPhoneCode ? "发送中..." : phoneCooldown > 0 ? `${phoneCooldown}s 后重试` : "获取验证码"}
                  </button>
                </div>
                {phoneDemoCode ? <p className="text-[14px] text-[#315efb]">演示验证码：{phoneDemoCode}</p> : null}
                {notice ? <p className="text-[14px] text-[#315efb]">{notice}</p> : null}
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
            ) : (
              <form className="space-y-6" onSubmit={handleEmailLogin}>
                <input
                  className="h-[64px] w-full rounded-[16px] border border-[#e4e9f2] bg-[#f7f9fc] px-7 text-[18px] text-[#172033] outline-none transition placeholder:text-[#b7c1cf] focus:border-[#c9d8f9] focus:bg-white focus:shadow-[0_0_0_4px_rgba(49,94,251,0.05)]"
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="请输入邮箱"
                  value={email}
                />
                <div className="grid grid-cols-[1fr_auto] gap-4">
                  <input
                    className="h-[64px] rounded-[16px] border border-[#e4e9f2] bg-[#f7f9fc] px-7 text-[18px] text-[#172033] outline-none transition placeholder:text-[#b7c1cf] focus:border-[#c9d8f9] focus:bg-white focus:shadow-[0_0_0_4px_rgba(49,94,251,0.05)]"
                    onChange={(event) => setEmailCode(event.target.value)}
                    placeholder="请输入邮箱验证码"
                    value={emailCode}
                  />
                  <button
                    className="h-[64px] rounded-[16px] border border-[#dbe3ef] px-6 text-[16px] font-semibold text-[#315efb] transition hover:bg-[#f4f8ff] disabled:opacity-60"
                    disabled={sendingEmailCode || emailCooldown > 0}
                    onClick={handleSendEmailCode}
                    type="button"
                  >
                    {sendingEmailCode ? "发送中..." : emailCooldown > 0 ? `${emailCooldown}s 后重试` : "获取验证码"}
                  </button>
                </div>
                {emailDemoCode ? <p className="text-[14px] text-[#315efb]">演示验证码：{emailDemoCode}</p> : null}
                {notice ? <p className="text-[14px] text-[#315efb]">{notice}</p> : null}
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
